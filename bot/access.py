from bot.config import settings
from models.enums import UserRole
from models.user import User


def is_admin_user(user: User | None) -> bool:
    return bool(user and user.role == UserRole.admin)


def can_receive_bot_responses(user: User | None) -> bool:
    if not settings.RESPOND_ONLY_TO_ADMINS:
        return True
    return is_admin_user(user)
