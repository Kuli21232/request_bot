"""Маршрутизация заявок по ключевым словам и regex из таблицы routing_rules."""
import re
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.routing import RoutingRule
from models.department import Department
from bot.database import AsyncSessionLocal


class AutoRouter:
    def __init__(self):
        self.last_match_reason: str | None = None

    async def suggest_department(
        self,
        text: str,
        group_id: int,
        exclude_department_id: int | None = None,
    ) -> Department | None:
        """
        Проверяет text против активных routing_rules.
        Возвращает Department если найдено совпадение, иначе None.
        """
        self.last_match_reason = None
        if not text:
            return None

        text_lower = text.lower()

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(RoutingRule)
                .join(Department, Department.id == RoutingRule.department_id)
                .where(Department.group_id == group_id)
                .where(Department.is_active == True)
                .where(RoutingRule.is_active == True)
            )
            rules: list[RoutingRule] = list(result.scalars().all())

            for rule in rules:
                if rule.department_id == exclude_department_id:
                    continue

                matched = False
                if rule.pattern_type == "keyword":
                    matched = rule.pattern.lower() in text_lower
                elif rule.pattern_type == "regex":
                    try:
                        matched = bool(re.search(rule.pattern, text, re.IGNORECASE))
                    except re.error:
                        pass

                if matched:
                    # Увеличиваем счётчик совпадений
                    rule.match_count += 1
                    await session.commit()

                    dept_result = await session.execute(
                        select(Department).where(Department.id == rule.department_id)
                    )
                    dept = dept_result.scalar_one_or_none()
                    if dept:
                        self.last_match_reason = (
                            f"правило #{rule.id} ({rule.pattern_type}: \"{rule.pattern}\")"
                        )
                        return dept

        return None
