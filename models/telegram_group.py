from sqlalchemy import BigInteger, Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


class TelegramGroup(Base, TimestampMixin):
    __tablename__ = "telegram_groups"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    departments: Mapped[list["Department"]] = relationship(
        "Department", back_populates="group", cascade="all, delete-orphan"
    )
    topics: Mapped[list["TelegramTopic"]] = relationship(
        "TelegramTopic", back_populates="group", cascade="all, delete-orphan"
    )
    requests: Mapped[list["Request"]] = relationship(
        "Request", back_populates="group"
    )
