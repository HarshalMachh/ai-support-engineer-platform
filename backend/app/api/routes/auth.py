from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rate_limit import auth_rate_limit
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserRead
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(auth_rate_limit)],
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = auth_service.register_customer(db, payload)
    return auth_service.issue_token(user)


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(auth_rate_limit)])
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = auth_service.authenticate(db, payload)
    return auth_service.issue_token(user)


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> User:
    return user
