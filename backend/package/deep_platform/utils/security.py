from datetime import datetime, timedelta, timezone
from jose import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerifyMismatchError, VerificationError
from deep_platform.config import settings

_ph = PasswordHasher()

def hash_password(p: str) -> str:
    return _ph.hash(p)

def verify_password(plain: str, hashed: str) -> bool:
    if not hashed or not hashed.startswith("$argon2"):
        return False
    try:
        return _ph.verify(hashed, plain)
    except (InvalidHash, VerifyMismatchError, VerificationError):
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
