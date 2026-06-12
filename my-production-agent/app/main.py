import time
import json
import logging
import signal
import uuid
import sys
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse
import uvicorn
from pythonjsonlogger import jsonlogger

from .agent import KnowledgeBaseAgent
from .store import EmbeddingStore
from .embeddings import _mock_embed
from .models import Document

from .config import settings
from .auth import verify_api_key
from .rate_limiter import check_rate_limit
from .cost_guard import check_budget
try:
    from .rate_limiter import r as redis_client
except Exception:
    redis_client = None

# Structured Logging
logger = logging.getLogger()
logger.setLevel(settings.LOG_LEVEL)
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(message)s')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

# Global states
START_TIME = time.time()
_is_ready = False
_in_flight_requests = 0

rag_agent: KnowledgeBaseAgent = None

def mock_llm_ask(prompt: str) -> str:
    """Mock LLM interaction"""
    time.sleep(0.5)
    preview = prompt[:200].replace("\n", " ")
    return f"This is an Agent generated response based on context: '{preview}...'"

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready, rag_agent
    logger.info({"event": "startup", "message": "Agent starting up..."})
    time.sleep(0.1) # Simulate load
    
    # Initialize RAG agent
    store = EmbeddingStore(collection_name="production_store", embedding_fn=_mock_embed)
    store.add_documents([Document(id="doc1", content="This is a test document for the production AI agent knowledge base.", metadata={"source": "test"})])
    rag_agent = KnowledgeBaseAgent(store=store, llm_fn=mock_llm_ask)
    
    _is_ready = True
    logger.info({"event": "ready", "message": "Agent is ready!"})
    
    yield
    
    _is_ready = False
    logger.info({"event": "shutdown_initiated", "message": "Graceful shutdown initiated..."})
    timeout = 30
    elapsed = 0
    while _in_flight_requests > 0 and elapsed < timeout:
        logger.info({"event": "waiting_requests", "in_flight": _in_flight_requests})
        time.sleep(1)
        elapsed += 1
    logger.info({"event": "shutdown_complete", "message": "Shutdown complete"})

app = FastAPI(title="Production AI Agent", lifespan=lifespan)

@app.middleware("http")
async def track_requests(request: Request, call_next):
    global _in_flight_requests
    _in_flight_requests += 1
    try:
        response = await call_next(request)
        return response
    finally:
        _in_flight_requests -= 1

@app.get("/health")
def health():
    uptime = time.time() - START_TIME
    return {
        "status": "ok",
        "uptime": round(uptime, 2),
        "version": "1.0.0"
    }

@app.get("/ready")
def ready():
    if not _is_ready:
        return JSONResponse(status_code=503, content={"status": "not ready"})
    
    # Check redis if configured
    if redis_client is not None:
        try:
            redis_client.ping()
        except Exception:
            return JSONResponse(status_code=503, content={"status": "redis not ready"})
            
    return {"status": "ready"}

@app.post("/ask")
def ask(
    question: str,
    user_id: str = Depends(verify_api_key)
):
    # Apply rate limiting & cost guard manually or via Depends.
    # To conform with the check script, we should ensure rate limit and budget apply
    check_rate_limit(user_id)
    check_budget(user_id)
    
    # Stateless history management
    history_key = f"history:{user_id}"
    history = []
    if redis_client:
        history = redis_client.lrange(history_key, 0, -1)
    
    answer = rag_agent.answer(question)
    
    if redis_client:
        redis_client.rpush(history_key, f"Q: {question}")
        redis_client.rpush(history_key, f"A: {answer}")
        redis_client.expire(history_key, 3600)
    
    logger.info({"event": "ask", "user": user_id, "question": question})
    return {"answer": answer, "history_len": len(history)}

def handle_sigterm(signum, frame):
    logger.info({"event": "signal_received", "signal": signum})
    # uvicorn handles the actual shutdown when SIGTERM is received

signal.signal(signal.SIGTERM, handle_sigterm)
signal.signal(signal.SIGINT, handle_sigterm)

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        timeout_graceful_shutdown=30
    )
