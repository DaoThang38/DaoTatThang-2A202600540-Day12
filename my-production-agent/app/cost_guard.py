import redis
from datetime import datetime
from fastapi import HTTPException
from .config import settings

# Use the same redis connection strategy
try:
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
except Exception:
    r = None

def check_budget(user_id: str, estimated_cost: float = 0.01):
    if r is None:
        return True
    
    month_key = datetime.now().strftime("%Y-%m")
    key = f"budget:{user_id}:{month_key}"
    
    current = float(r.get(key) or 0)
    if current + estimated_cost > settings.MONTHLY_BUDGET_USD:
        raise HTTPException(status_code=402, detail="Payment Required: Monthly budget exceeded")
    
    pipe = r.pipeline()
    pipe.incrbyfloat(key, estimated_cost)
    pipe.expire(key, 32 * 24 * 3600)  # 32 days
    pipe.execute()
    return True
