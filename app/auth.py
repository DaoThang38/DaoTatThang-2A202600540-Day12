from fastapi import Header, HTTPException, Security
from fastapi.security import APIKeyHeader
from .config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(api_key_header: str = Security(api_key_header)):
    if not api_key_header:
        raise HTTPException(status_code=401, detail="API Key missing")
    if api_key_header != settings.AGENT_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    # Return a mocked user_id based on the key
    return "user_from_api_key"
