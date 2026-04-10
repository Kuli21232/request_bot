from sqlalchemy import BigInteger, Boolean, Enum as SAEnum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from sqlalchemy import DateTime, func

from models.base import Base, TimestampMixin
from models.enums import UserRole

DEFAULT_NOTIFICATION_PREFS = {
    "on_status_change": True,
    "on_assignment": True,
    "on_comment": True,
    "digest_frequency": "daily",
}


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    # bcrypt hash — только для admin-пользователей сайта
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language_code: Mapped[str] = mapped_column(String(10), default="ru", nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role", values_callable=lambda x: [e.value for e in x], create_type=False),
        default=UserRole.user, nullable=False
    )
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notification_preferences: Mapped[dict] = mapped_column(
        JSONB, default=DEFAULT_NOTIFICATION_PREFS, nullable=False
    )
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    submitted_requests: Mapped[list["Request"]] = relationship(
        "Request", back_populates="submitter", foreign_keys="Request.submitter_id"
    )
    assigned_requests: Mapped[list["Request"]] = relationship(
        "Request", back_populates="assigned_to", foreign_keys="Request.assigned_to_id"
    )
    comments: Mapped[list["RequestComment"]] = relationship(
        "RequestComment", back_populates="author"
    )
    department_memberships: Mapped[list["DepartmentAgent"]] = relationship(
        "DepartmentAgent", back_populates="agent"
    )
    profile_notes: Mapped[list["UserProfileNote"]] = relationship(
        "UserProfileNote", foreign_keys="UserProfileNote.target_user_id", back_populates="target_user"
    )
    authored_profile_notes: Mapped[list["UserProfileNote"]] = relationship(
        "UserProfileNote", foreign_keys="UserProfileNote.author_id", back_populates="author"
    )
    profile_subscriptions: Mapped[list["UserProfileSubscription"]] = relationship(
        "UserProfileSubscription", foreign_keys="UserProfileSubscription.watcher_user_id", back_populates="watcher"
    )
    profile_watchers: Mapped[list["UserProfileSubscription"]] = relationship(
        "UserProfileSubscription", foreign_keys="UserProfileSubscription.target_user_id", back_populates="target_user"
    )
    submitted_signals: Mapped[list["FlowSignal"]] = relationship(
        "FlowSignal", foreign_keys="FlowSignal.submitter_id", back_populates="submitter"
    )
    responsible_flow_cases: Mapped[list["FlowCase"]] = relationship(
        "FlowCase", foreign_keys="FlowCase.responsible_user_id", back_populates="responsible_user"
    )
    assigned_flow_cases: Mapped[list["FlowCase"]] = relationship(
        "FlowCase", foreign_keys="FlowCase.assigned_by_user_id", back_populates="assigned_by"
    )
    profile_ai_snapshot: Mapped["UserProfileAISnapshot | None"] = relationship(
        "UserProfileAISnapshot", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
