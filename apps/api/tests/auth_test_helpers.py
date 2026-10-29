"""Issue fixture tokens bound to the persisted account, like the login route."""
from app.database import SessionLocal
from app.models import User
from app.security import create_access_token as _issue


def create_access_token(subject: str, credential_hash: str | None = None) -> str:
    if credential_hash is None:
        with SessionLocal() as db:
            user = db.get(User, subject)
            assert user is not None, "Fixture must persist its account before token issuance"
            credential_hash = user.password_hash
    return _issue(subject, credential_hash)
