from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.request import Request, RequestComment, RequestHistory
from models.enums import RequestStatus, RequestPriority


class RequestRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        group_id: int,
        department_id: int,
        submitter_id: int,
        body: str,
        telegram_message_id: int,
        telegram_topic_id: int | None,
        telegram_chat_id: int,
        attachments: list | None = None,
        auto_routed: bool = False,
        routing_reason: str | None = None,
        is_duplicate: bool = False,
        duplicate_of_id: int | None = None,
        similarity_score: float | None = None,
    ) -> Request:
        req = Request(
            ticket_number="",  # будет задан триггером PostgreSQL
            group_id=group_id,
            department_id=department_id,
            submitter_id=submitter_id,
            body=body,
            telegram_message_id=telegram_message_id,
            telegram_topic_id=telegram_topic_id,
            telegram_chat_id=telegram_chat_id,
            attachments=attachments or [],
            auto_routed=auto_routed,
            routing_reason=routing_reason,
            is_duplicate=is_duplicate,
            duplicate_of_id=duplicate_of_id,
            similarity_score=similarity_score,
        )
        self.session.add(req)
        await self.session.flush()   # получаем id и ticket_number из триггера
        await self.session.commit()
        await self.session.refresh(req)
        return req

    async def get_by_id(self, request_id: int) -> Request | None:
        result = await self.session.execute(
            select(Request)
            .options(
                selectinload(Request.submitter),
                selectinload(Request.assigned_to),
                selectinload(Request.department),
                selectinload(Request.comments),
            )
            .where(Request.id == request_id)
        )
        return result.scalar_one_or_none()

    async def get_by_ticket(self, ticket_number: str) -> Request | None:
        result = await self.session.execute(
            select(Request).where(Request.ticket_number == ticket_number)
        )
        return result.scalar_one_or_none()

    async def get_open_by_department(self, department_id: int, limit: int = 50) -> list[Request]:
        result = await self.session.execute(
            select(Request)
            .where(Request.department_id == department_id)
            .where(Request.status.not_in([RequestStatus.resolved, RequestStatus.closed, RequestStatus.duplicate]))
            .order_by(Request.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent_by_department(
        self, department_id: int, hours: int = 48, limit: int = 100
    ) -> list[Request]:
        """Для поиска дублей — последние заявки в отделе."""
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        result = await self.session.execute(
            select(Request)
            .where(Request.department_id == department_id)
            .where(Request.created_at >= since)
            .where(Request.is_duplicate == False)
            .order_by(Request.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_status(
        self, request_id: int, status: RequestStatus, actor_id: int | None = None
    ) -> None:
        req = await self.get_by_id(request_id)
        if req is None:
            return
        old_status = req.status
        req.status = status
        if status in (RequestStatus.resolved, RequestStatus.closed):
            req.resolved_at = datetime.now(timezone.utc)
        self.session.add(
            RequestHistory(
                request_id=request_id,
                actor_id=actor_id,
                action="status_change",
                field_name="status",
                old_value=old_status.value,
                new_value=status.value,
            )
        )
        await self.session.commit()

    async def assign(self, request_id: int, agent_id: int, actor_id: int | None = None) -> None:
        req = await self.get_by_id(request_id)
        if req is None:
            return
        old_agent = req.assigned_to_id
        req.assigned_to_id = agent_id
        if req.status == RequestStatus.new:
            req.status = RequestStatus.open
        self.session.add(
            RequestHistory(
                request_id=request_id,
                actor_id=actor_id,
                action="assignment",
                field_name="assigned_to_id",
                old_value=str(old_agent),
                new_value=str(agent_id),
            )
        )
        await self.session.commit()

    async def add_comment(
        self,
        request_id: int,
        author_id: int,
        body: str,
        is_internal: bool = False,
        is_system: bool = False,
        telegram_message_id: int | None = None,
    ) -> RequestComment:
        comment = RequestComment(
            request_id=request_id,
            author_id=author_id,
            body=body,
            is_internal=is_internal,
            is_system=is_system,
            telegram_message_id=telegram_message_id,
        )
        self.session.add(comment)
        # Обновляем first_response_at если агент отвечает первый раз
        req = await self.get_by_id(request_id)
        if req and req.first_response_at is None and not is_system:
            req.first_response_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(comment)
        return comment

    async def get_sla_breached(self) -> list[Request]:
        """Заявки у которых дедлайн прошёл но sla_breached ещё False."""
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(Request)
            .where(Request.sla_deadline <= now)
            .where(Request.sla_breached == False)
            .where(Request.status.not_in([RequestStatus.resolved, RequestStatus.closed]))
        )
        return list(result.scalars().all())

    async def mark_sla_breached(self, request_id: int) -> None:
        await self.session.execute(
            update(Request).where(Request.id == request_id).values(sla_breached=True)
        )
        await self.session.commit()
