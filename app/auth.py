import os
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN

# Load the API key from environment variables
API_KEY = os.getenv("API_KEY", "your-super-secret-api-key-here")
API_KEY_NAME = "X-API-Key"

# Define the security scheme
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Verifies the incoming API key.
    Returns the API key if valid, otherwise raises 403.
    """
    if api_key != API_KEY:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Invalid API Key. Please provide a valid X-API-Key header."
        )
    return api_key