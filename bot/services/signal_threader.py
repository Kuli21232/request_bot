from dataclasses import dataclass

from rapidfuzz import fuzz

from bot.database.repositories.flow_repo import FlowRepository
from models.flow import FlowCase


@dataclass
class CaseMatchResult:
    case: FlowCase | None
    score: float
    reason: str | None = None


class SignalThreader:
    def __init__(self, threshold: float = 0.72):
        self.threshold = threshold

    async def match_case(
        self,
        repo: FlowRepository,
        *,
        group_id: int,
        department_id: int | None,
        summary: str | None,
        body: str,
        case_key: str | None,
        store: str | None,
        topic_id: int | None = None,
        kind: str | None = None,
    ) -> CaseMatchResult:
        candidates = await repo.find_case_candidates(
            group_id=group_id,
            department_id=department_id,
            case_key=case_key,
            store=store,
            topic_id=topic_id,
            kind=kind,
        )
        if not candidates:
            return CaseMatchResult(case=None, score=0.0)

        if case_key:
            for case in candidates:
                if (case.ai_labels or {}).get("case_key") == case_key:
                    return CaseMatchResult(case=case, score=1.0, reason=f"case_key={case_key}")

        source_text = " ".join(part for part in [summary, body, store] if part).lower()
        best_case = None
        best_score = 0.0
        for case in candidates:
            case_text = " ".join(
                part for part in [case.title, case.summary or "", " ".join(case.stores_affected or [])] if part
            ).lower()
            # Combine multiple fuzzy metrics for a more robust score:
            # token_set_ratio: good for reordered/superset matches
            # token_sort_ratio: good for paraphrases with same words
            # partial_ratio: good for short summaries matching longer case text
            tsr = fuzz.token_set_ratio(source_text, case_text) / 100.0
            ts_sort = fuzz.token_sort_ratio(source_text, case_text) / 100.0
            partial = fuzz.partial_ratio(source_text, case_text) / 100.0
            score = tsr * 0.5 + ts_sort * 0.3 + partial * 0.2
            if score > best_score:
                best_score = score
                best_case = case

        # When candidates were narrowed by topic+kind we can use a lower bar:
        # same topic + same signal kind is already strong signal of relatedness.
        effective_threshold = 0.45 if (topic_id is not None and kind is not None) else self.threshold
        if best_case and best_score >= effective_threshold:
            return CaseMatchResult(case=best_case, score=round(best_score, 3), reason="similarity")

        return CaseMatchResult(case=None, score=round(best_score, 3))
