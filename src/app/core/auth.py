# src/app/core/auth.py
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime, timezone
from config import SECRET_KEY, ALGORITHM
from .jwt_key import load_hmac_key

security = HTTPBearer(auto_error=True)
SIGNING_KEY = load_hmac_key(SECRET_KEY)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = (credentials.credentials or "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")

    try:
        # exp 검증은 PyJWT가 기본 수행 (verify_exp=True)
        payload = jwt.decode(token, SIGNING_KEY, algorithms=[ALGORITHM])

        # 혹시 exp가 숫자로 들어온 경우 직접 한 번 더 방어적으로 확인
        exp = payload.get("exp")
        if isinstance(exp, (int, float)):
            now = datetime.now(timezone.utc).timestamp()
            if exp < now:
                raise HTTPException(status_code=401, detail="Token expired")

        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidSignatureError:
        raise HTTPException(status_code=401, detail="Invalid signature")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
