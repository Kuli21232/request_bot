"""One-shot training and verification runner for the bot AI layer."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging

from bot.database import AsyncSessionLocal
from bot.database.repositories.topic_repo import TopicRepository
from bot.services.assistant_service import AssistantService
from bot.services.topic_automation_service import TopicAutomationService
from bot.services.topic_learning_service import TopicLearningService
from bot.services.user_profile_ai_service import UserProfileAIService

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train topic and profile AI snapshots.")
    parser.add_argument("--topics-limit", type=int, default=30, help="Maximum active topics to retrain.")
    parser.add_argument(
        "--automation-limit",
        type=int,
        default=30,
        help="Maximum active topics to refresh in automation snapshots.",
    )
    parser.add_argument(
        "--profiles-limit",
        type=int,
        default=40,
        help="Maximum active user profiles to refresh.",
    )
    parser.add_argument(
        "--force-topics",
        action="store_true",
        help="Retrain active topics even if they look up to date.",
    )
    parser.add_argument(
        "--verify-query",
        type=str,
        default="сделай сводку по ЕГАИС",
        help="Assistant query used for smoke verification.",
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip assistant smoke verification after training.",
    )
    parser.add_argument("--json", action="store_true", help="Print result as JSON.")
    return parser


async def _force_retrain_topics(session, *, limit: int) -> list[dict]:
    topic_repo = TopicRepository(session)
    trainer = TopicLearningService()
    topics = await topic_repo.list_topics()
    results: list[dict] = []

    for topic in topics:
        if not topic.is_active or topic.profile is None or topic.last_message_at is None:
            continue
        trained = await trainer.retrain_topic(session, topic.id)
        if trained:
            results.append(trained)
        if len(results) >= limit:
            break
    return results


async def run_training(args: argparse.Namespace) -> dict:
    async with AsyncSessionLocal() as session:
        trainer = TopicLearningService()
        automation = TopicAutomationService()
        profiles = UserProfileAIService()

        if args.force_topics:
            topic_results = await _force_retrain_topics(session, limit=args.topics_limit)
        else:
            topic_results = await trainer.retrain_active_topics(session, limit=args.topics_limit)

        automation_results = await automation.refresh_active_topics(session, limit=args.automation_limit)
        profile_results = await profiles.refresh_active_snapshots(session, limit=args.profiles_limit)

        verification: dict | None = None
        if not args.skip_verify:
            assistant = AssistantService(session)
            answer = await assistant.answer(args.verify_query)
            verification = {
                "query": args.verify_query,
                "mode": answer.mode,
                "used_llm": answer.used_llm,
                "answer": answer.answer,
            }

        await session.commit()

    return {
        "topics_retrained": len(topic_results),
        "topic_titles": [item.get("topic_title") or item.get("title") for item in topic_results[:8]],
        "automation_refreshed": len(automation_results),
        "profiles_refreshed": len(profile_results),
        "profile_ids": profile_results[:12],
        "verification": verification,
    }


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    args = build_parser().parse_args()
    result = asyncio.run(run_training(args))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"Topics retrained: {result['topics_retrained']}")
    if result["topic_titles"]:
        print("Topic titles: " + ", ".join(result["topic_titles"]))
    print(f"Automation refreshed: {result['automation_refreshed']}")
    print(f"Profiles refreshed: {result['profiles_refreshed']}")
    if result["profile_ids"]:
        print("Profile IDs: " + ", ".join(str(item) for item in result["profile_ids"]))
    if result["verification"]:
        verification = result["verification"]
        print("Verification query: " + verification["query"])
        print(f"Verification mode: {verification['mode']}, used_llm={verification['used_llm']}")
        print("Verification answer: " + verification["answer"])


if __name__ == "__main__":
    main()
