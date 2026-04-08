"""Нечёткий поиск дублей среди последних заявок отдела."""
from dataclasses import dataclass

from rapidfuzz import fuzz

from bot.config import settings
from bot.database import AsyncSessionLocal
from bot.database.repositories.request_repo import RequestRepository


@dataclass
class DuplicateResult:
    is_duplicate: bool
    original_id: int | None = None
    original_ticket: str | None = None
    score: float | None = None


class DuplicateDetector:
    def __init__(self, threshold: float | None = None):
        self.threshold = threshold or settings.DUPLICATE_SIMILARITY_THRESHOLD

    async def find_duplicate(
        self,
        content: str,
        department_id: int,
        submitter_id: int,
    ) -> DuplicateResult:
        if not content or len(content.strip()) < 10:
            return DuplicateResult(is_duplicate=False)

        async with AsyncSessionLocal() as session:
            repo = RequestRepository(session)
            candidates = await repo.get_recent_by_department(
                department_id=department_id, hours=72, limit=200
            )

        best_score = 0.0
        best_match = None

        for candidate in candidates:
            # Не проверяем заявки самого пользователя (это не дубль, а уточнение)
            if candidate.submitter_id == submitter_id:
                continue
            score = fuzz.token_set_ratio(content.lower(), candidate.body.lower()) / 100.0
            if score > best_score:
                best_score = score
                best_match = candidate

        if best_score >= self.threshold and best_match is not None:
            return DuplicateResult(
                is_duplicate=True,
                original_id=best_match.id,
                original_ticket=best_match.ticket_number,
                score=round(best_score, 3),
            )

        return DuplicateResult(is_duplicate=False)
