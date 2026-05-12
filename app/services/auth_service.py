"""User lookup and password verification."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models.user import User


def authenticate_user(session: Session, *, email: str, password: str) -> User | None:
    """Return the user if credentials match an active account, else None."""
    stmt = select(User).where(User.email == email.lower().strip())
    user = session.scalars(stmt).first()
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def get_user_by_id(session: Session, user_id: int) -> User | None:
    """Return the user by primary key, or None if not found."""
    return session.get(User, user_id)
