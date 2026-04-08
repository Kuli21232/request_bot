from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


class FlowCase(Base, TimestampMixin):
    __tablename__ = "flow_cases"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("telegram_groups.id"), nullable=False)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    primary_topic_id: Mapped[int | None] = mapped_column(ForeignKey("telegram_topics.id"), nullable=True)
    request_id: Mapped[int | None] = mapped_column(ForeignKey("requests.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
    priority: Mapped[str] = mapped_column(String(32), default="normal", nullable=False)
    kind: Mapped[str] = mapped_column(String(64), default="signal_cluster", nullable=False)
    suggested_owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    owners: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    stores_affected: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    ai_labels: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_confidence: Mapped[float | None] = mapped_column(nullable=True)
    last_signal_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    signal_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    media_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    department: Mapped["Department | None"] = relationship("Department")
    primary_topic: Mapped["TelegramTopic | None"] = relationship("TelegramTopic")
    suggested_owner: Mapped["User | None"] = relationship("User")
    request: Mapped["Request | None"] = relationship("Request")
    signals: Mapped[list["FlowSignal"]] = relationship("FlowSignal", back_populates="case")


class FlowSignal(Base, TimestampMixin):
    __tablename__ = "flow_signals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("telegram_groups.id"), nullable=False)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("telegram_topics.id"), nullable=True)
    submitter_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    request_id: Mapped[int | None] = mapped_column(ForeignKey("requests.id"), nullable=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("flow_cases.id"), nullable=True)
    duplicate_signal_id: Mapped[int | None] = mapped_column(ForeignKey("flow_signals.id"), nullable=True)
    source_topic_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_message_id: Mapped[int] = mapped_column(Integer, nullable=False)
    source_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    store: Mapped[str | None] = mapped_column(String(255), nullable=True)
    kind: Mapped[str] = mapped_column(String(64), default="request", nullable=False)
    importance: Mapped[str] = mapped_column(String(32), default="normal", nullable=False)
    actionability: Mapped[str] = mapped_column(String(64), default="digest_only", nullable=False)
    case_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    topic_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_labels: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    entities: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    media_flags: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    attachments: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    has_media: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_attention: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_noise: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    digest_bucket: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ai_confidence: Mapped[float | None] = mapped_column(nullable=True)
    happened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    case: Mapped["FlowCase | None"] = relationship("FlowCase", back_populates="signals", foreign_keys=[case_id])
    duplicate_signal: Mapped["FlowSignal | None"] = relationship(
        "FlowSignal", remote_side="FlowSignal.id", foreign_keys=[duplicate_signal_id]
    )
    department: Mapped["Department | None"] = relationship("Department")
    topic: Mapped["TelegramTopic | None"] = relationship("TelegramTopic")
    request: Mapped["Request | None"] = relationship("Request")
    submitter: Mapped["User | None"] = relationship("User")
    media_items: Mapped[list["SignalMedia"]] = relationship(
        "SignalMedia", back_populates="signal", cascade="all, delete-orphan"
    )


class SignalMedia(Base, TimestampMixin):
    __tablename__ = "signal_media"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    signal_id: Mapped[int] = mapped_column(ForeignKey("flow_signals.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    telegram_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telegram_file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    original_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    compressed_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    preview_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    storage_meta: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    signal: Mapped["FlowSignal"] = relationship("FlowSignal", back_populates="media_items")
