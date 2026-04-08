from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.department import Department
from models.telegram_group import TelegramGroup


class DepartmentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_topic(self, chat_id: int, topic_id: int) -> Department | None:
        result = await self.session.execute(
            select(Department)
            .join(TelegramGroup, TelegramGroup.id == Department.group_id)
            .where(TelegramGroup.telegram_chat_id == chat_id)
            .where(Department.telegram_topic_id == topic_id)
            .where(Department.is_active == True)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, dept_id: int) -> Department | None:
        result = await self.session.execute(
            select(Department).where(Department.id == dept_id)
        )
        return result.scalar_one_or_none()

    async def get_all_by_group(self, group_id: int) -> list[Department]:
        result = await self.session.execute(
            select(Department)
            .where(Department.group_id == group_id)
            .where(Department.is_active == True)
            .order_by(Department.sort_order)
        )
        return list(result.scalars().all())

    async def create(
        self,
        group_id: int,
        telegram_topic_id: int,
        name: str,
        sla_hours: int = 24,
        icon_emoji: str | None = None,
        description: str | None = None,
    ) -> Department:
        dept = Department(
            group_id=group_id,
            telegram_topic_id=telegram_topic_id,
            name=name,
            sla_hours=sla_hours,
            icon_emoji=icon_emoji,
            description=description,
        )
        self.session.add(dept)
        await self.session.commit()
        await self.session.refresh(dept)
        return dept

    async def ensure_group_exists(self, chat_id: int, title: str) -> TelegramGroup:
        result = await self.session.execute(
            select(TelegramGroup).where(TelegramGroup.telegram_chat_id == chat_id)
        )
        group = result.scalar_one_or_none()
        if group is None:
            group = TelegramGroup(telegram_chat_id=chat_id, title=title)
            self.session.add(group)
            await self.session.commit()
            await self.session.refresh(group)
        return group
