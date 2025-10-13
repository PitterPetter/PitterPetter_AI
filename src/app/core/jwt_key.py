# src/app/core/jwt_key.py
import base64
import binascii

def load_hmac_key(secret: str) -> bytes:
    s = (secret or "").strip()                 # 앞뒤 공백/개행 제거
    s = s.replace("\n", "").replace("\r", "")  # 개행 정리
    try:
        # Spring은 Base64.getDecoder().decode() 사용 → 엄격 디코딩과 유사
        decoded = base64.b64decode(s, validate=True)
        # HS256은 최소 256bit(=32바이트) 권장. 너무 짧으면 원문 바이트로 사용.
        if len(decoded) >= 32:
            return decoded
        # 디코딩이 되긴 했지만 너무 짧으면 키로 부적절 → 원문 사용
        return s.encode("utf-8")
    except (binascii.Error, ValueError):
        # 아예 Base64가 아니면 원문 바이트 사용 (Spring의 catch 분기와 동일)
        return s.encode("utf-8")
