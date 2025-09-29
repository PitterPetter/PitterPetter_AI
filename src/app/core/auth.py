# src/app/core/auth.py
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt  # PyJWT
from datetime import datetime

security = HTTPBearer()
SECRET_KEY = "너만의_시크릿키"   # 환경변수로 관리 추천
ALGORITHM = "HS256"

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # payload 안에는 user_id, exp(만료시간) 등이 들어있음
        if payload.get("exp") < datetime.utcnow().timestamp():
            raise HTTPException(status_code=401, detail="Token expired")
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
