from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError, ConflictError
from app.core.logging import get_logger
from app.core.security import create_access_token, hash_password, verify_password
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserRead

logger = get_logger(__name__)

# Pre-computed hash used to keep login timing similar for unknown emails.
_DUMMY_HASH = hash_password("timing-attack-dummy-password")


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower()))


def register_customer(db: Session, payload: RegisterRequest) -> User:
    """Public registration always creates CUSTOMER accounts; staff are created by seed/admins."""
    if get_user_by_email(db, payload.email):
        raise ConflictError("An account with this email already exists")
    user = User(
        name=payload.name,
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role=UserRole.CUSTOMER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("User registered", extra={"operation": "auth.register", "success": True})
    return user


def authenticate(db: Session, payload: LoginRequest) -> User:
    user = get_user_by_email(db, payload.email)
    if user is None:
        verify_password(payload.password, _DUMMY_HASH)
        raise AuthenticationError("Invalid email or password")
    if not verify_password(payload.password, user.password_hash):
        raise AuthenticationError("Invalid email or password")
    if not user.is_active:
        raise AuthenticationError("This account has been deactivated")
    return user


def issue_token(user: User) -> TokenResponse:
    settings = get_settings()
    return TokenResponse(
        access_token=create_access_token(user.id, user.role.value),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserRead.model_validate(user),
    )
