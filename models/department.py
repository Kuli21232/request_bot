from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String, Text, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


class Department(Base, TimestampMixin):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("telegram_groups.id", ondelete="CASCADE"), nullable=False
    )
    telegram_topic_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon_emoji: Mapped[str | None] = mapped_column(String(10), nullable=True)
    color_hex: Mapped[str] = mapped_column(String(7), default="#6B7280", nullable=False)
    sla_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    group: Mapped["TelegramGroup"] = relationship("TelegramGroup", back_populates="departments")
    requests: Mapped[list["Request"]] = relationship("Request", back_populates="department")
    routing_rules: Mapped[list["RoutingRule"]] = relationship(
        "RoutingRule", back_populates="department", cascade="all, delete-orphan"
    )
    canned_responses: Mapped[list["CannedResponse"]] = relationship(
        "CannedResponse", back_populates="department"
    )
    agents: Mapped[list["DepartmentAgent"]] = relationship(
        "DepartmentAgent", back_populates="department", cascade="all, delete-orphan"
    )
