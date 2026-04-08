from datetime import datetime
from sqlalchemy import (
    BigInteger, Boolean, DateTime, Enum as SAEnum, Float,
    ForeignKey, Integer, String, Text, func,
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin
from models.enums import RequestStatus, RequestPriority


class Request(Base, TimestampMixin):
    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticket_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("telegram_groups.id"), nullable=False
    )
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id"), nullable=False
    )
    submitter_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    assigned_to_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    # Контент
    subject: Mapped[str | None] = mapped_column(String(512), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    attachments: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # Telegram-метаданные
    telegram_message_id: Mapped[int] = mapped_column(Integer, nullable=False)
    telegram_topic_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Статус и классификация
    status: Mapped[RequestStatus] = mapped_column(
        SAEnum(RequestStatus, name="request_status", values_callable=lambda x: [e.value for e in x], create_type=False),
        default=RequestStatus.new, nullable=False
    )
    priority: Mapped[RequestPriority] = mapped_column(
        SAEnum(RequestPriority, name="request_priority", values_callable=lambda x: [e.value for e in x], create_type=False),
        default=RequestPriority.normal, nullable=False
    )
    tags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # SLA
    sla_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sla_breached: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    first_response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Дубликаты
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    duplicate_of_id: Mapped[int | None] = mapped_column(
        ForeignKey("requests.id"), nullable=True
    )
    similarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Маршрутизация
    auto_routed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    routing_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # AI-классификация
    ai_subject: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ai_category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ai_sentiment: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Обратная связь
    satisfaction_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    satisfaction_comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Отношения
    group: Mapped["TelegramGroup"] = relationship("TelegramGroup", back_populates="requests")
    department: Mapped["Department"] = relationship("Department", back_populates="requests")
    submitter: Mapped["User"] = relationship(
        "User", back_populates="submitted_requests", foreign_keys=[submitter_id]
    )
    assigned_to: Mapped["User | None"] = relationship(
        "User", back_populates="assigned_requests", foreign_keys=[assigned_to_id]
    )
    comments: Mapped[list["RequestComment"]] = relationship(
        "RequestComment", back_populates="request", cascade="all, delete-orphan"
    )
    history: Mapped[list["RequestHistory"]] = relationship(
        "RequestHistory", back_populates="request", cascade="all, delete-orphan"
    )
    duplicate_of: Mapped["Request | None"] = relationship(
        "Request", remote_side="Request.id", foreign_keys=[duplicate_of_id]
    )


class RequestComment(Base, TimestampMixin):
    __tablename__ = "request_comments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(
        ForeignKey("requests.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attachments: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    telegram_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    request: Mapped["Request"] = relationship("Request", back_populates="comments")
    author: Mapped["User"] = relationship("User", back_populates="comments")


class RequestHistory(Base):
    __tablename__ = "request_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(
        ForeignKey("requests.id", ondelete="CASCADE"), nullable=False
    )
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    field_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    request: Mapped["Request"] = relationship("Request", back_populates="history")
