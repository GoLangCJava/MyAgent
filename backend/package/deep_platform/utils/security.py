from datetime import datetime, timedelta, timezone
from jose import jwt
import bcrypt
from deep_platform.config import settings

def _to_72(p: str) -> bytes:
    # bcrypt 上限 72 字节, 超长截断 (与经典 bcrypt 语义一致, 避免新版抛 ValueError)
    return p.encode("utf-8")[:72]

def hash_password(p: str) -> str:
    return bcrypt.hashpw(_to_72(p), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_to_72(plain), hashed.encode("utf-8"))
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def decode_token(token: str):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except Exception:
        return None
