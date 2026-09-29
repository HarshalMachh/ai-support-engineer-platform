from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.enums import UserRole
from app.models.user import User


def list_users(
    db: Session, role: UserRole | None, search: str | None, page: int, page_size: int
) -> tuple[list[User], int]:
    stmt = select(User)
    if role:
        stmt = stmt.where(User.role == role)
    if search:
        pattern = f"%{search.strip().lower()}%"
        stmt = stmt.where(or_(func.lower(User.name).like(pattern), func.lower(User.email).like(pattern)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    users = db.scalars(
        stmt.order_by(User.role, User.name).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return list(users), total


def list_staff(db: Session) -> list[User]:
    return list(
        db.scalars(
            select(User)
            .where(User.role.in_((UserRole.AGENT, UserRole.ADMIN)), User.is_active.is_(True))
            .order_by(User.name)
        ).all()
    )
