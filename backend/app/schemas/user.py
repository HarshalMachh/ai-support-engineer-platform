from datetime import datetime

from app.models.enums import UserRole
from app.schemas.common import ORMModel


class UserBrief(ORMModel):
    id: int
    name: str
    email: str
    role: UserRole


class UserRead(UserBrief):
    is_active: bool
    created_at: datetime
    updated_at: datetime
