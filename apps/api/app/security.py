from datetime import datetime, timedelta, timezone
import hashlib
import secrets
import bcrypt
import jwt

from .config import settings

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_password_reset_token() -> str:
    return secrets.token_urlsafe(32)


def hash_password_reset_token(token: str) -> str:
    # Keep deterministic hashing for indexed token lookup while using
    # a computationally expensive KDF rather than a fast hash primitive.
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        token.encode("utf-8"),
        settings.jwt_secret.encode("utf-8"),
        600_000,
        dklen=32,
    )
    return digest.hex()
