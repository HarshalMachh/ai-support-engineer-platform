from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_admin, require_staff
from app.db.session import get_db
from app.models.enums import UserRole
from app.schemas.common import Page
from app.schemas.user import UserBrief, UserRead
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=Page[UserRead], dependencies=[Depends(require_admin)])
def list_users(
    role: UserRole | None = None,
    search: str | None = Query(default=None, max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> Page[UserRead]:
    users, total = user_service.list_users(db, role, search, page, page_size)
    return Page[UserRead].build([UserRead.model_validate(u) for u in users], total, page, page_size)


@router.get("/agents", response_model=list[UserBrief], dependencies=[Depends(require_staff)])
def list_agents(db: Session = Depends(get_db)) -> list[UserBrief]:
    return [UserBrief.model_validate(u) for u in user_service.list_staff(db)]
