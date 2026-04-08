from sqlalchemy import Boolean, Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin
from models.enums import RequestPriority, UserRole


class RoutingRule(Base, TimestampMixin):
    __tablename__ = "routing_rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE"), nullable=False
    )
    pattern: Mapped[str] = mapped_column(Text, nullable=False)
    pattern_type: Mapped[str] = mapped_column(String(20), default="keyword", nullable=False)
    priority_boost: Mapped[RequestPriority | None] = mapped_column(
        SAEnum(RequestPriority, name="request_priority", values_callable=lambda x: [e.value for e in x], create_type=False), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    match_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    department: Mapped["Department"] = relationship("Department", back_populates="routing_rules")


class CannedResponse(Base, TimestampMixin):
    __tablename__ = "canned_responses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[str | None] = mapped_column(String(500), nullable=True)
    use_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    department: Mapped["Department | None"] = relationship(
        "Department", back_populates="canned_responses"
    )


class DepartmentAgent(Base):
    __tablename__ = "department_agents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE"), nullable=False
    )
    agent_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    is_supervisor: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    department: Mapped["Department"] = relationship("Department", back_populates="agents")
    agent: Mapped["User"] = relationship("User", back_populates="department_memberships")


class NotificationQueue(Base):
    __tablename__ = "notifications_queue"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), default="telegram", nullable=False)
    payload: Mapped[dict] = mapped_column(__import__("sqlalchemy.dialects.postgresql", fromlist=["JSONB"]).JSONB, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    from datetime import datetime
    from sqlalchemy import DateTime, func
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
