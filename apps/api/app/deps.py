from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from hashlib import sha256
import secrets
import re
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import User

bearer = HTTPBearer(auto_error=True)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    settings.validate_signing_configuration()
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm], options={"require": ["sub", "exp", "cv"]})
        user_id = payload["sub"]
        if not isinstance(user_id, str) or not user_id or len(user_id) > 128:
            raise ValueError("Invalid subject")
        if type(payload["exp"]) is not int or not isinstance(payload["cv"], str) or not re.fullmatch(r"[0-9a-f]{64}", payload["cv"]):
            raise ValueError("Invalid credential claims")
    except (jwt.InvalidTokenError, ValueError, TypeError, OverflowError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    # Every route requires current credentials. Versionless legacy sessions must
    # sign in again; no Authored/generated mode exempts session revocation.
    if not secrets.compare_digest(payload["cv"], sha256(user.password_hash.encode()).hexdigest()):
        raise HTTPException(status_code=401,detail="Session credentials changed; sign in again")
    request.state.user_id = user.id
    return user
