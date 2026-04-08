from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


class TelegramTopic(Base, TimestampMixin):
    __tablename__ = "telegram_topics"
    __table_args__ = (
        UniqueConstraint("group_id", "telegram_topic_id", name="uq_telegram_topic_group_thread"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("telegram_groups.id", ondelete="CASCADE"), nullable=False)
    telegram_topic_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    icon_emoji: Mapped[str | None] = mapped_column(String(32), nullable=True)
    topic_kind: Mapped[str] = mapped_column(String(64), default="mixed", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    media_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    signal_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    profile_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    group: Mapped["TelegramGroup"] = relationship("TelegramGroup", back_populates="topics")
    profile: Mapped["TopicAIProfile | None"] = relationship(
        "TopicAIProfile",
        back_populates="topic",
        uselist=False,
        cascade="all, delete-orphan",
    )


class TopicAIProfile(Base, TimestampMixin):
    __tablename__ = "topic_ai_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("telegram_topics.id", ondelete="CASCADE"), nullable=False, unique=True)
    preferred_department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    profile_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    allowed_signal_types: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    default_actions: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    priority_rules: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    media_policy: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    examples: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    learning_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    behavior_rules: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    confidence_threshold: Mapped[float] = mapped_column(Float, default=0.65, nullable=False)
    auto_learn_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_retrained_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_rule_update_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    topic: Mapped["TelegramTopic"] = relationship("TelegramTopic", back_populates="profile")
    preferred_department: Mapped["Department | None"] = relationship("Department")
