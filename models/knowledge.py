from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


class KnowledgeArticle(Base, TimestampMixin):
    __tablename__ = "knowledge_articles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(String(512), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    audience: Mapped[str] = mapped_column(String(50), default="all", nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    created_by: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_id])
    updated_by: Mapped["User | None"] = relationship("User", foreign_keys=[updated_by_id])


class UserProfileNote(Base):
    __tablename__ = "user_profile_notes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    target_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    notify_target: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    target_user: Mapped["User"] = relationship("User", foreign_keys=[target_user_id], back_populates="profile_notes")
    author: Mapped["User | None"] = relationship("User", foreign_keys=[author_id], back_populates="authored_profile_notes")


class UserProfileSubscription(Base, TimestampMixin):
    __tablename__ = "user_profile_subscriptions"
    __table_args__ = (
        UniqueConstraint("watcher_user_id", "target_user_id", name="uq_profile_subscription"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    watcher_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    target_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_types: Mapped[list] = mapped_column(JSONB, default=lambda: ["profile_note"], nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    watcher: Mapped["User"] = relationship("User", foreign_keys=[watcher_user_id], back_populates="profile_subscriptions")
    target_user: Mapped["User"] = relationship("User", foreign_keys=[target_user_id], back_populates="profile_watchers")
