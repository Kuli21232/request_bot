from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo


def build_request_created_keyboard(
    ticket_number: str,
    mini_app_url: str,
    request_id: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📋 Открыть заявку",
                    web_app=WebAppInfo(url=mini_app_url),
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Мои заявки",
                    callback_data="my_requests",
                )
            ],
        ]
    )


def build_status_keyboard(request_id: int) -> InlineKeyboardMarkup:
    from models.enums import RequestStatus
    statuses = [
        (RequestStatus.open, "🔵 Открыта"),
        (RequestStatus.in_progress, "🟡 В работе"),
        (RequestStatus.waiting_for_user, "⏳ Ожидание"),
        (RequestStatus.resolved, "✅ Решена"),
        (RequestStatus.closed, "🔒 Закрыта"),
    ]
    buttons = [
        [InlineKeyboardButton(
            text=label,
            callback_data=f"status:{request_id}:{status.value}",
        )]
        for status, label in statuses
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_priority_keyboard(request_id: int) -> InlineKeyboardMarkup:
    priorities = [
        ("low", "🟢 Низкий"),
        ("normal", "🔵 Обычный"),
        ("high", "🟠 Высокий"),
        ("critical", "🔴 Критический"),
    ]
    buttons = [
        [InlineKeyboardButton(
            text=label,
            callback_data=f"priority:{request_id}:{prio}",
        )]
        for prio, label in priorities
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_rating_keyboard(request_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⭐ 1", callback_data=f"rate:{request_id}:1"),
                InlineKeyboardButton(text="⭐ 2", callback_data=f"rate:{request_id}:2"),
                InlineKeyboardButton(text="⭐ 3", callback_data=f"rate:{request_id}:3"),
                InlineKeyboardButton(text="⭐ 4", callback_data=f"rate:{request_id}:4"),
                InlineKeyboardButton(text="⭐ 5", callback_data=f"rate:{request_id}:5"),
            ]
        ]
    )
