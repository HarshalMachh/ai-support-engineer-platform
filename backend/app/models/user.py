from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.db.types import string_enum
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.ticket import Ticket


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(string_enum(UserRole), nullable=False, default=UserRole.CUSTOMER)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    customer_tickets: Mapped[list["Ticket"]] = relationship(
        back_populates="customer", foreign_keys="Ticket.customer_id"
    )
    assigned_tickets: Mapped[list["Ticket"]] = relationship(
        back_populates="assigned_agent", foreign_keys="Ticket.assigned_agent_id"
    )

    __table_args__ = (Index("ix_users_role", "role"),)

    def __repr__(self) -> str:
        return f"<User id={self.id} role={self.role}>"
