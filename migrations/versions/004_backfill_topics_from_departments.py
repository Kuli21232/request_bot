"""backfill topics from departments

Revision ID: 004
Revises: 003
Create Date: 2026-04-08
"""

from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO telegram_topics (
            group_id,
            telegram_topic_id,
            title,
            icon_emoji,
            topic_kind,
            is_active,
            message_count,
            media_count,
            signal_count,
            profile_version,
            created_at,
            updated_at
        )
        SELECT
            d.group_id,
            d.telegram_topic_id,
            d.name,
            d.icon_emoji,
            'mixed',
            d.is_active,
            0,
            0,
            0,
            1,
            now(),
            now()
        FROM departments d
        WHERE NOT EXISTS (
            SELECT 1
            FROM telegram_topics t
            WHERE t.group_id = d.group_id
              AND t.telegram_topic_id = d.telegram_topic_id
        )
        """
    )

    op.execute(
        """
        INSERT INTO topic_ai_profiles (
            topic_id,
            preferred_department_id,
            profile_summary,
            allowed_signal_types,
            default_actions,
            priority_rules,
            media_policy,
            examples,
            learning_snapshot,
            behavior_rules,
            confidence_threshold,
            auto_learn_enabled,
            created_at,
            updated_at
        )
        SELECT
            t.id,
            d.id,
            'Автосозданный профиль из существующего operational отдела',
            jsonb_build_array('request', 'status_update', 'chat/noise'),
            jsonb_build_object('fallback', 'digest_only', 'media_only', 'digest_only'),
            jsonb_build_object('default', 'normal', 'with_media_boost', false),
            jsonb_build_object('store_preview_in_db', true, 'image_max_side', 1280, 'image_quality', 60),
            '[]'::jsonb,
            '{}'::jsonb,
            jsonb_build_object('topic_kind', 'mixed', 'strict_allowed_types', false),
            0.65,
            true,
            now(),
            now()
        FROM telegram_topics t
        JOIN departments d
          ON d.group_id = t.group_id
         AND d.telegram_topic_id = t.telegram_topic_id
        WHERE NOT EXISTS (
            SELECT 1
            FROM topic_ai_profiles p
            WHERE p.topic_id = t.id
        )
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM topic_ai_profiles
        WHERE profile_summary = 'Автосозданный профиль из существующего operational отдела'
        """
    )
    op.execute(
        """
        DELETE FROM telegram_topics
        WHERE id NOT IN (SELECT topic_id FROM topic_ai_profiles)
          AND message_count = 0
          AND signal_count = 0
        """
    )
