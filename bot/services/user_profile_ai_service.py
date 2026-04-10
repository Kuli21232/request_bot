from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.enums import UserRole
from models.flow import FlowCase, FlowSignal, SignalMedia
from models.knowledge import UserProfileAISnapshot, UserProfileNote, UserProfileSubscription
from models.topic import TelegramTopic
from models.user import User

STAFF_ROLES = {UserRole.agent, UserRole.supervisor, UserRole.admin}


class UserProfileAIService:
    async def refresh_snapshot(self, session: AsyncSession, user_id: int) -> UserProfileAISnapshot | None:
        user = await session.get(User, user_id)
        if user is None:
            return None

        signals = await self._list_user_signals(session, user_id, limit=160)
        assigned_cases = await self._list_assigned_cases(session, user_id, limit=40)
        analysis = self._build_analysis(user, signals, assigned_cases)

        result = await session.execute(
            select(UserProfileAISnapshot).where(UserProfileAISnapshot.user_id == user_id)
        )
        snapshot = result.scalar_one_or_none()
        if snapshot is None:
            snapshot = UserProfileAISnapshot(user_id=user_id)
            session.add(snapshot)

        snapshot.summary = analysis["summary"]
        snapshot.dominant_topics = analysis["dominant_topics"]
        snapshot.assigned_case_stats = analysis["assigned_case_stats"]
        snapshot.recommendations = analysis["recommendations"]
        snapshot.analysis = analysis["analysis"]
        snapshot.last_analyzed_at = datetime.now(timezone.utc)
        await session.flush()
        return snapshot

    async def refresh_active_snapshots(self, session: AsyncSession, *, limit: int = 40) -> list[int]:
        candidate_ids: list[int] = []

        recent_signal_users = await session.execute(
            select(FlowSignal.submitter_id)
            .where(FlowSignal.submitter_id.is_not(None))
            .order_by(FlowSignal.happened_at.desc())
            .limit(limit * 4)
        )
        candidate_ids.extend(
            user_id for user_id in recent_signal_users.scalars().all() if user_id is not None
        )

        assigned_case_users = await session.execute(
            select(FlowCase.responsible_user_id)
            .where(FlowCase.responsible_user_id.is_not(None))
            .order_by(FlowCase.updated_at.desc())
            .limit(limit * 2)
        )
        candidate_ids.extend(
            user_id for user_id in assigned_case_users.scalars().all() if user_id is not None
        )

        refreshed: list[int] = []
        seen: set[int] = set()
        for user_id in candidate_ids:
            if user_id in seen:
                continue
            seen.add(user_id)
            snapshot = await self.refresh_snapshot(session, user_id)
            if snapshot is not None:
                refreshed.append(user_id)
            if len(refreshed) >= limit:
                break
        return refreshed

    async def build_profile_payload(
        self,
        session: AsyncSession,
        *,
        target_user: User,
        viewer_user: User,
    ) -> dict:
        snapshot = await self.refresh_snapshot(session, target_user.id)
        signals = await self._list_user_signals(session, target_user.id, limit=160)
        assigned_cases = await self._list_assigned_cases(session, target_user.id, limit=30)

        can_view_internal = viewer_user.role in STAFF_ROLES
        is_self = viewer_user.id == target_user.id

        notes: list[UserProfileNote] = []
        subscription = None
        watchers_count = 0
        if can_view_internal:
            notes = await self._list_profile_notes(session, target_user.id, limit=30)
            if not is_self:
                subscription = await self._get_subscription(session, viewer_user.id, target_user.id)
            watchers_count = await self._count_watchers(session, target_user.id)

        topic_groups = self._build_topic_groups(signals)
        media_items = self._collect_media(topic_groups)

        return {
            "id": target_user.id,
            "telegram_user_id": target_user.telegram_user_id,
            "first_name": target_user.first_name,
            "last_name": target_user.last_name,
            "username": target_user.username,
            "email": target_user.email,
            "role": target_user.role.value,
            "is_banned": target_user.is_banned,
            "last_active_at": target_user.last_active_at.isoformat() if target_user.last_active_at else None,
            "created_at": target_user.created_at.isoformat() if target_user.created_at else None,
            "notes": [self._serialize_note(note) for note in notes],
            "notes_count": len(notes),
            "is_watching": bool(subscription and subscription.is_active),
            "watchers_count": watchers_count,
            "assigned_cases": [self._serialize_case(case) for case in assigned_cases],
            "topic_groups": topic_groups,
            "media_items": media_items,
            "ai_summary": snapshot.summary if snapshot else None,
            "ai_recommendations": list(snapshot.recommendations or []) if snapshot else [],
            "ai_snapshot": self._serialize_snapshot(snapshot),
            "permissions": {
                "is_self": is_self,
                "can_view_team": viewer_user.role in STAFF_ROLES,
                "can_view_internal_notes": can_view_internal,
                "can_assign_responsible": viewer_user.role in STAFF_ROLES,
            },
        }

    async def build_team_metrics(self, session: AsyncSession, users: list[User]) -> dict[int, dict]:
        user_ids = [user.id for user in users]
        if not user_ids:
            return {}

        assigned_counts = {
            row.user_id: row.count
            for row in (
                await session.execute(
                    select(
                        FlowCase.responsible_user_id.label("user_id"),
                        func.count(FlowCase.id).label("count"),
                    )
                    .where(FlowCase.responsible_user_id.in_(user_ids))
                    .where(FlowCase.status.in_(["open", "watching"]))
                    .group_by(FlowCase.responsible_user_id)
                )
            ).all()
        }
        critical_counts = {
            row.user_id: row.count
            for row in (
                await session.execute(
                    select(
                        FlowCase.responsible_user_id.label("user_id"),
                        func.count(FlowCase.id).label("count"),
                    )
                    .where(FlowCase.responsible_user_id.in_(user_ids))
                    .where(FlowCase.status.in_(["open", "watching"]))
                    .where(FlowCase.is_critical == True)
                    .group_by(FlowCase.responsible_user_id)
                )
            ).all()
        }
        recent_signal_counts = {
            row.user_id: row.count
            for row in (
                await session.execute(
                    select(
                        FlowSignal.submitter_id.label("user_id"),
                        func.count(FlowSignal.id).label("count"),
                    )
                    .where(FlowSignal.submitter_id.in_(user_ids))
                    .group_by(FlowSignal.submitter_id)
                )
            ).all()
        }
        snapshot_result = await session.execute(
            select(UserProfileAISnapshot).where(UserProfileAISnapshot.user_id.in_(user_ids))
        )
        snapshots = {item.user_id: item for item in snapshot_result.scalars().all()}

        data: dict[int, dict] = {}
        for user in users:
            snapshot = snapshots.get(user.id)
            data[user.id] = {
                "assigned_open_case_count": assigned_counts.get(user.id, 0),
                "critical_case_count": critical_counts.get(user.id, 0),
                "submitted_signal_count": recent_signal_counts.get(user.id, 0),
                "ai_summary": snapshot.summary if snapshot else None,
                "top_topics": list(snapshot.dominant_topics[:3]) if snapshot else [],
            }
        return data

    async def _list_user_signals(self, session: AsyncSession, user_id: int, *, limit: int) -> list[FlowSignal]:
        result = await session.execute(
            select(FlowSignal)
            .options(
                selectinload(FlowSignal.topic).selectinload(TelegramTopic.group),
                selectinload(FlowSignal.case).selectinload(FlowCase.primary_topic),
                selectinload(FlowSignal.request),
                selectinload(FlowSignal.media_items),
                selectinload(FlowSignal.department),
            )
            .where(FlowSignal.submitter_id == user_id)
            .order_by(FlowSignal.happened_at.desc(), FlowSignal.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def _list_assigned_cases(self, session: AsyncSession, user_id: int, *, limit: int) -> list[FlowCase]:
        result = await session.execute(
            select(FlowCase)
            .options(
                selectinload(FlowCase.primary_topic).selectinload(TelegramTopic.group),
                selectinload(FlowCase.request),
                selectinload(FlowCase.suggested_owner),
                selectinload(FlowCase.responsible_user),
            )
            .where(FlowCase.responsible_user_id == user_id)
            .order_by(FlowCase.is_critical.desc(), FlowCase.last_signal_at.desc().nullslast(), FlowCase.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def _list_profile_notes(self, session: AsyncSession, user_id: int, *, limit: int) -> list[UserProfileNote]:
        result = await session.execute(
            select(UserProfileNote)
            .options(selectinload(UserProfileNote.author))
            .where(UserProfileNote.target_user_id == user_id)
            .order_by(UserProfileNote.created_at.desc(), UserProfileNote.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def _get_subscription(self, session: AsyncSession, watcher_user_id: int, target_user_id: int) -> UserProfileSubscription | None:
        result = await session.execute(
            select(UserProfileSubscription).where(
                UserProfileSubscription.watcher_user_id == watcher_user_id,
                UserProfileSubscription.target_user_id == target_user_id,
            )
        )
        return result.scalar_one_or_none()

    async def _count_watchers(self, session: AsyncSession, target_user_id: int) -> int:
        result = await session.execute(
            select(func.count(UserProfileSubscription.id)).where(
                UserProfileSubscription.target_user_id == target_user_id,
                UserProfileSubscription.is_active == True,
            )
        )
        return int(result.scalar_one() or 0)

    def _build_analysis(self, user: User, signals: list[FlowSignal], assigned_cases: list[FlowCase]) -> dict:
        topic_counts = Counter()
        attention_by_topic = Counter()
        kind_counts = Counter()
        media_count = 0

        for signal in signals:
            topic_key = self._topic_key(signal)
            topic_counts[topic_key] += 1
            kind_counts[signal.kind or "request"] += 1
            if signal.requires_attention:
                attention_by_topic[topic_key] += 1
            media_count += len(signal.media_items or [])

        dominant_topics = []
        for topic_key, count in topic_counts.most_common(6):
            dominant_topics.append(
                {
                    "topic_title": topic_key,
                    "count": count,
                    "attention_count": attention_by_topic.get(topic_key, 0),
                }
            )

        open_cases = [case for case in assigned_cases if case.status in {"open", "watching"}]
        critical_cases = [case for case in open_cases if case.is_critical or case.priority == "critical"]

        recommendations: list[str] = []
        if critical_cases:
            titles = ", ".join(case.title for case in critical_cases[:3])
            recommendations.append(f"Сначала разберите критичные ситуации: {titles}.")
        if open_cases:
            recommendations.append(f"На пользователе сейчас {len(open_cases)} открытых ситуаций, проверьте их статус и следующий шаг.")
        if dominant_topics:
            topic_title = dominant_topics[0]["topic_title"]
            recommendations.append(f"Основной поток пользователя сейчас в теме «{topic_title}», там стоит смотреть новые сообщения в первую очередь.")
        if media_count:
            recommendations.append(f"У пользователя есть {media_count} вложений в потоке, просмотрите медиа как подтверждение по открытым темам.")
        if not recommendations:
            recommendations.append("Пока профиль спокойный: открытых ответственностей нет, можно наблюдать за новыми сообщениями.")

        summary = self._build_summary(user, dominant_topics, open_cases, critical_cases, kind_counts)
        analysis = {
            "top_kinds": dict(kind_counts.most_common(6)),
            "signal_count": len(signals),
            "media_count": media_count,
            "last_signal_at": signals[0].happened_at.isoformat() if signals else None,
            "open_assigned_case_titles": [case.title for case in open_cases[:8]],
            "critical_assigned_case_titles": [case.title for case in critical_cases[:5]],
        }
        assigned_case_stats = {
            "open_count": len(open_cases),
            "critical_count": len(critical_cases),
            "total_count": len(assigned_cases),
        }
        return {
            "summary": summary,
            "dominant_topics": dominant_topics,
            "assigned_case_stats": assigned_case_stats,
            "recommendations": recommendations[:6],
            "analysis": analysis,
        }

    def _build_summary(
        self,
        user: User,
        dominant_topics: list[dict],
        open_cases: list[FlowCase],
        critical_cases: list[FlowCase],
        kind_counts: Counter,
    ) -> str:
        full_name = " ".join(part for part in [user.first_name, user.last_name] if part).strip() or "Пользователь"
        topic_part = "без выраженных тем"
        if dominant_topics:
            topic_labels = ", ".join(item["topic_title"] for item in dominant_topics[:3])
            topic_part = f"чаще всего пишет в топики: {topic_labels}"

        kind_part = ""
        if kind_counts:
            kind_label = kind_counts.most_common(1)[0][0]
            kind_part = f", основной тип потока: {kind_label}"

        responsibility_part = "ответственности не назначены"
        if open_cases:
            responsibility_part = f"на пользователе {len(open_cases)} открытых ситуаций"
            if critical_cases:
                responsibility_part += f", из них {len(critical_cases)} критичные"

        return f"{full_name}: {topic_part}{kind_part}; {responsibility_part}."

    def _build_topic_groups(self, signals: list[FlowSignal]) -> list[dict]:
        buckets: dict[str, dict] = {}
        for signal in signals:
            topic_id = signal.topic_id or 0
            topic_title = signal.topic.title if signal.topic else signal.topic_label or "Без топика"
            group_title = signal.topic.group.title if signal.topic and signal.topic.group else None
            key = f"{topic_id}:{topic_title}"
            bucket = buckets.get(key)
            if bucket is None:
                bucket = {
                    "topic_id": signal.topic_id,
                    "topic_title": topic_title,
                    "group_title": group_title,
                    "signal_count": 0,
                    "request_count": 0,
                    "case_count": 0,
                    "media_count": 0,
                    "requires_attention_count": 0,
                    "last_activity_at": None,
                    "items": [],
                    "_case_ids": set(),
                }
                buckets[key] = bucket

            bucket["signal_count"] += 1
            if signal.request_id:
                bucket["request_count"] += 1
            if signal.case_id and signal.case_id not in bucket["_case_ids"]:
                bucket["_case_ids"].add(signal.case_id)
                bucket["case_count"] += 1
            if signal.requires_attention:
                bucket["requires_attention_count"] += 1
            bucket["media_count"] += len(signal.media_items or [])
            if bucket["last_activity_at"] is None:
                bucket["last_activity_at"] = signal.happened_at.isoformat() if signal.happened_at else None
            bucket["items"].append(self._serialize_signal(signal))

        groups = list(buckets.values())
        for group in groups:
            group.pop("_case_ids", None)
        groups.sort(
            key=lambda item: (
                item["requires_attention_count"],
                item["signal_count"],
                item["last_activity_at"] or "",
            ),
            reverse=True,
        )
        return groups

    def _collect_media(self, topic_groups: list[dict], *, limit: int = 24) -> list[dict]:
        media_items: list[dict] = []
        for group in topic_groups:
            for item in group["items"]:
                for media in item.get("media", []):
                    media_items.append(
                        {
                            **media,
                            "topic_id": group["topic_id"],
                            "topic_title": group["topic_title"],
                            "group_title": group["group_title"],
                            "signal_id": item["id"],
                            "signal_summary": item["summary"] or item["body"],
                            "happened_at": item["happened_at"],
                        }
                    )
        media_items.sort(key=lambda item: item.get("happened_at") or "", reverse=True)
        return media_items[:limit]

    @staticmethod
    def _topic_key(signal: FlowSignal) -> str:
        if signal.topic and signal.topic.title:
            return signal.topic.title
        return signal.topic_label or "Без топика"

    @staticmethod
    def _serialize_snapshot(snapshot: UserProfileAISnapshot | None) -> dict | None:
        if snapshot is None:
            return None
        return {
            "summary": snapshot.summary,
            "dominant_topics": list(snapshot.dominant_topics or []),
            "assigned_case_stats": dict(snapshot.assigned_case_stats or {}),
            "recommendations": list(snapshot.recommendations or []),
            "analysis": dict(snapshot.analysis or {}),
            "last_analyzed_at": snapshot.last_analyzed_at.isoformat() if snapshot.last_analyzed_at else None,
        }

    @staticmethod
    def _serialize_case(flow_case: FlowCase) -> dict:
        return {
            "id": flow_case.id,
            "title": flow_case.title,
            "summary": flow_case.summary,
            "status": flow_case.status,
            "priority": flow_case.priority,
            "is_critical": flow_case.is_critical,
            "signal_count": flow_case.signal_count,
            "recommended_action": flow_case.recommended_action,
            "primary_topic_id": flow_case.primary_topic_id,
            "primary_topic_title": flow_case.primary_topic.title if flow_case.primary_topic else None,
            "group_title": flow_case.primary_topic.group.title if flow_case.primary_topic and flow_case.primary_topic.group else None,
            "request_id": flow_case.request_id,
            "request_ticket": flow_case.request.ticket_number if flow_case.request else None,
            "suggested_owner_id": flow_case.suggested_owner_id,
            "suggested_owner_name": flow_case.suggested_owner.first_name if flow_case.suggested_owner else None,
            "responsible_user_id": flow_case.responsible_user_id,
            "responsible_user_name": flow_case.responsible_user.first_name if flow_case.responsible_user else None,
            "assigned_at": flow_case.assigned_at.isoformat() if flow_case.assigned_at else None,
            "last_signal_at": flow_case.last_signal_at.isoformat() if flow_case.last_signal_at else None,
        }

    def _serialize_signal(self, signal: FlowSignal) -> dict:
        return {
            "id": signal.id,
            "kind": signal.kind,
            "importance": signal.importance,
            "summary": signal.summary,
            "body": signal.body,
            "store": signal.store,
            "topic_id": signal.topic_id,
            "topic_title": signal.topic.title if signal.topic else signal.topic_label,
            "case_id": signal.case_id,
            "case_title": signal.case.title if signal.case else None,
            "request_id": signal.request_id,
            "request_ticket": signal.request.ticket_number if signal.request else None,
            "has_media": signal.has_media,
            "requires_attention": signal.requires_attention,
            "happened_at": signal.happened_at.isoformat() if signal.happened_at else signal.created_at.isoformat(),
            "media": [self._serialize_media(item) for item in signal.media_items or []],
        }

    @staticmethod
    def _serialize_media(media: SignalMedia) -> dict:
        return {
            "id": media.id,
            "kind": media.kind,
            "mime_type": media.mime_type,
            "file_name": media.file_name,
            "width": media.width,
            "height": media.height,
            "duration_seconds": media.duration_seconds,
            "preview_url": f"/api/v1/flow/media/{media.id}/preview",
            "content_url": f"/api/v1/flow/media/{media.id}/content",
            "has_preview": media.preview_bytes is not None,
            "can_open_content": bool(media.preview_bytes is not None or media.telegram_file_path),
        }

    @staticmethod
    def _serialize_note(note: UserProfileNote) -> dict:
        return {
            "id": note.id,
            "body": note.body,
            "notify_target": note.notify_target,
            "author_id": note.author_id,
            "author_name": note.author.first_name if note.author else None,
            "created_at": note.created_at.isoformat() if note.created_at else None,
        }
