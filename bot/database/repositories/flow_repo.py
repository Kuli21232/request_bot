from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.flow import FlowCase, FlowSignal, SignalMedia


class FlowRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_signal(self, **kwargs) -> FlowSignal:
        signal = FlowSignal(**kwargs)
        self.session.add(signal)
        await self.session.flush()
        return signal

    async def create_signal_media(self, **kwargs) -> SignalMedia:
        media = SignalMedia(**kwargs)
        self.session.add(media)
        await self.session.flush()
        return media

    async def list_recent_signals(
        self,
        *,
        group_id: int,
        department_id: int | None = None,
        hours: int = 72,
        limit: int = 200,
    ) -> list[FlowSignal]:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        q = (
            select(FlowSignal)
            .where(FlowSignal.group_id == group_id)
            .where(FlowSignal.happened_at >= since)
            .order_by(FlowSignal.happened_at.desc())
            .limit(limit)
        )
        if department_id is not None:
            q = q.where(FlowSignal.department_id == department_id)
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def list_topic_training_signals(
        self,
        *,
        topic_id: int,
        limit: int = 80,
    ) -> list[FlowSignal]:
        result = await self.session.execute(
            select(FlowSignal)
            .options(
                selectinload(FlowSignal.media_items),
                selectinload(FlowSignal.case),
            )
            .where(FlowSignal.topic_id == topic_id)
            .order_by(FlowSignal.happened_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_topic_cases(
        self,
        *,
        topic_id: int,
        limit: int = 20,
    ) -> list[FlowCase]:
        result = await self.session.execute(
            select(FlowCase)
            .options(
                selectinload(FlowCase.department),
                selectinload(FlowCase.primary_topic),
                selectinload(FlowCase.request),
            )
            .where(FlowCase.primary_topic_id == topic_id)
            .order_by(FlowCase.last_signal_at.desc().nullslast(), FlowCase.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_topic_signal_briefs(
        self,
        *,
        topic_id: int,
        limit: int = 5,
        kind: str | None = None,
        requires_attention: bool | None = None,
    ) -> list[FlowSignal]:
        query = (
            select(FlowSignal)
            .options(
                selectinload(FlowSignal.case),
                selectinload(FlowSignal.department),
                selectinload(FlowSignal.topic),
                selectinload(FlowSignal.request),
                selectinload(FlowSignal.submitter),
            )
            .where(FlowSignal.topic_id == topic_id)
        )
        if kind:
            query = query.where(FlowSignal.kind == kind)
        if requires_attention is not None:
            query = query.where(FlowSignal.requires_attention == requires_attention)
        result = await self.session.execute(
            query.order_by(FlowSignal.happened_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def find_case_candidates(
        self,
        *,
        group_id: int,
        department_id: int | None,
        case_key: str | None,
        store: str | None,
        topic_id: int | None = None,
        kind: str | None = None,
        limit: int = 50,
    ) -> list[FlowCase]:
        q = (
            select(FlowCase)
            .where(FlowCase.group_id == group_id)
            .where(FlowCase.status.in_(["open", "watching"]))
            .order_by(FlowCase.last_signal_at.desc().nullslast(), FlowCase.updated_at.desc())
            .limit(limit)
        )
        if department_id is not None:
            q = q.where(or_(FlowCase.department_id == department_id, FlowCase.department_id.is_(None)))
        if case_key:
            q = q.where(
                or_(
                    FlowCase.ai_labels["case_key"].astext == case_key,
                    func.lower(FlowCase.title).contains(case_key.lower()),
                )
            )
        elif store:
            q = q.where(or_(FlowCase.title.ilike(f"%{store}%"), FlowCase.summary.ilike(f"%{store}%")))
        elif topic_id is not None:
            # Narrow to cases that originated in the same topic and same kind.
            # This is the main lever that lets photo-reports and status updates
            # pile into one case per topic instead of creating a new one each time.
            q = q.where(FlowCase.primary_topic_id == topic_id)
            if kind:
                q = q.where(FlowCase.kind == kind)
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def create_case(self, **kwargs) -> FlowCase:
        case = FlowCase(**kwargs)
        self.session.add(case)
        await self.session.flush()
        return case

    async def touch_case_with_signal(
        self,
        case: FlowCase,
        *,
        signal_time: datetime | None,
        store: str | None,
        increment_media: bool,
        importance: str,
    ) -> FlowCase:
        case.signal_count += 1
        case.last_signal_at = signal_time or datetime.now(timezone.utc)
        if increment_media:
            case.media_count += 1
        if importance in {"high", "critical"}:
            case.priority = importance
        if importance == "critical":
            case.is_critical = True
        if store and store not in case.stores_affected:
            case.stores_affected = [*case.stores_affected, store]
        await self.session.flush()
        return case
