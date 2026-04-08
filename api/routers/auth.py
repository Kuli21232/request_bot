"""Аутентификация: Telegram initData → JWT, email/password → JWT."""
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote

logger = logging.getLogger(__name__)

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from jose import jwt
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import api_settings
from api.dependencies import get_db

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _create_jwt(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=api_settings.JWT_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire},
        api_settings.API_SECRET_KEY,
        algorithm="HS256",
    )


# ── Telegram initData auth (Mini App) ─────────────────────────

class TelegramAuthRequest(BaseModel):
    init_data: str


@router.post("/telegram")
async def auth_telegram(body: TelegramAuthRequest, db: AsyncSession = Depends(get_db)):
    """Валидирует Telegram WebApp initData и возвращает JWT."""
    raw = unquote(body.init_data)
    parsed: dict[str, str] = {}
    for part in raw.split("&"):
        if "=" in part:
            k, v = part.split("=", 1)
            parsed[k] = v

    logger.info("Auth attempt. Keys received: %s", list(parsed.keys()))

    received_hash = parsed.pop("hash", "")
    if not received_hash:
        logger.warning("Auth failed: missing hash. Raw data (first 200): %s", raw[:200])
        raise HTTPException(status_code=401, detail="Missing hash")

    check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret_key = hmac.new(
        b"WebAppData", api_settings.BOT_TOKEN.encode(), hashlib.sha256
    ).digest()
    expected_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()

    logger.info("Hash check: received=%s..., expected=%s...", received_hash[:16], expected_hash[:16])

    if not hmac.compare_digest(received_hash, expected_hash):
        logger.warning("Auth failed: invalid signature. Check string: %s", check_string[:200])
        raise HTTPException(status_code=401, detail="Invalid signature")

    auth_date = int(parsed.get("auth_date", 0))
    if time.time() - auth_date > 86400:
        raise HTTPException(status_code=401, detail="Auth data expired")

    user_data = json.loads(parsed.get("user", "{}"))
    tg_user_id = user_data.get("id")
    if not tg_user_id:
        raise HTTPException(status_code=401, detail="No user in initData")

    from sqlalchemy import select
    from models.user import User

    result = await db.execute(select(User).where(User.telegram_user_id == tg_user_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            telegram_user_id=tg_user_id,
            first_name=user_data.get("first_name", ""),
            last_name=user_data.get("last_name"),
            username=user_data.get("username"),
            language_code=user_data.get("language_code", "ru"),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    token = _create_jwt(user.id)
    return {
        "token": token,
        "user": {
            "id": user.id,
            "telegram_user_id": user.telegram_user_id,
            "first_name": user.first_name,
            "username": user.username,
            "role": user.role.value,
        },
    }


# ── Email/password auth (веб-админка) ─────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
async def auth_login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Вход для администраторов через email/пароль."""
    from sqlalchemy import select
    from models.user import User
    from models.enums import UserRole

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user is None or user.password_hash is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not bcrypt.checkpw(body.password.encode(), user.password_hash.encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user.role not in (UserRole.agent, UserRole.supervisor, UserRole.admin):
        raise HTTPException(status_code=403, detail="Access denied")

    token = _create_jwt(user.id)
    return {
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "role": user.role.value,
        },
    }
