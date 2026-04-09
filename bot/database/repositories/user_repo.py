from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.knowledge import UserProfileNote, UserProfileSubscription
from models.user import User
from models.enums import UserRole


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_user_id: int) -> User | None:
        result = await self.session.execute(
            select(User).where(User.telegram_user_id == telegram_user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.session.execute(
            select(User)
            .options(
                selectinload(User.profile_notes).selectinload(UserProfileNote.author),
                selectinload(User.profile_watchers).selectinload(UserProfileSubscription.watcher),
            )
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def search_users(self, query: str | None = None, *, limit: int = 20) -> list[User]:
        stmt = select(User).where(User.is_banned == False)
        if query:
            cleaned = query.replace("@", "").strip()
            pattern = f"%{cleaned}%"
            if cleaned.isdigit():
                numeric = int(cleaned)
                stmt = stmt.where(
                    or_(
                        User.id == numeric,
                        User.telegram_user_id == numeric,
                        User.first_name.ilike(pattern),
                        User.last_name.ilike(pattern),
                        User.username.ilike(pattern),
                        User.email.ilike(pattern),
                    )
                )
            else:
                stmt = stmt.where(
                    or_(
                        User.first_name.ilike(pattern),
                        User.last_name.ilike(pattern),
                        User.username.ilike(pattern),
                        User.email.ilike(pattern),
                    )
                )
        stmt = stmt.order_by(User.first_name, User.last_name).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def upsert_telegram_user(
        self,
        telegram_user_id: int,
        first_name: str,
        last_name: str | None = None,
        username: str | None = None,
        language_code: str = "ru",
    ) -> User:
        user = await self.get_by_telegram_id(telegram_user_id)
        if user is None:
            user = User(
                telegram_user_id=telegram_user_id,
                first_name=first_name,
                last_name=last_name,
                username=username,
                language_code=language_code,
            )
            self.session.add(user)
        else:
            user.first_name = first_name
            user.last_name = last_name
            user.username = username
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_agents_by_department(self, department_id: int) -> list[User]:
        from models.routing import DepartmentAgent
        result = await self.session.execute(
            select(User)
            .join(DepartmentAgent, DepartmentAgent.agent_id == User.id)
            .where(DepartmentAgent.department_id == department_id)
            .where(User.is_banned == False)
        )
        return list(result.scalars().all())

    async def get_agent_with_min_load(self, department_id: int) -> User | None:
        """Возвращает агента с минимальным количеством открытых заявок."""
        from models.routing import DepartmentAgent
        from models.request import Request
        from models.enums import RequestStatus
        from sqlalchemy import func, outerjoin

        subq = (
            select(Request.assigned_to_id, func.count(Request.id).label("cnt"))
            .where(Request.status.in_([RequestStatus.new, RequestStatus.open, RequestStatus.in_progress]))
            .group_by(Request.assigned_to_id)
            .subquery()
        )

        result = await self.session.execute(
            select(User)
            .join(DepartmentAgent, DepartmentAgent.agent_id == User.id)
            .outerjoin(subq, subq.c.assigned_to_id == User.id)
            .where(DepartmentAgent.department_id == department_id)
            .where(User.is_banned == False)
            .order_by(func.coalesce(subq.c.cnt, 0))
            .limit(1)
        )
        return result.scalar_one_or_none()
