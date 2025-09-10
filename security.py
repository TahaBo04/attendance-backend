import os
from fastapi import HTTPException

SECRET_TOKEN = os.getenv("SECRET_TOKEN", "")  # set this on Render

def require_token(auth_header: str | None):
    if not SECRET_TOKEN:
        return  # no auth in dev
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = auth_header.split(" ", 1)[1].strip()
    if token != SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")
