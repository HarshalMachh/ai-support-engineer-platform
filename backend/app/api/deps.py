from collections.abc import Callable

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.logging import user_id_var
from app.core.security import TokenError, decode_access_token
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def user_from_token(db: Session, token: str) -> User:
    try:
        payload = decode_access_token(token)
    except TokenError as exc:
        raise AuthenticationError(exc.message, code="token_expired" if "expired" in exc.message else "invalid_token")
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise AuthenticationError("User not found or inactive", code="invalid_token")
    return user


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("Not authenticated", code="not_authenticated")
    user = user_from_token(db, credentials.credentials)
    request.state.user_id = user.id
    user_id_var.set(user.id)
    return user


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise PermissionDeniedError("You do not have permission to perform this action")
        return user

    return dependency


require_staff = require_roles(UserRole.AGENT, UserRole.ADMIN)
require_admin = require_roles(UserRole.ADMIN)
