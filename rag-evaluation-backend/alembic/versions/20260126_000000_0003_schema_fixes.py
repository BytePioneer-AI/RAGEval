"""Schema fixes: UUID default, JSONB defaults, updated_at triggers

Revision ID: 0003
Revises: 0002
Create Date: 2026-01-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.alter_column(
        "reports",
        "id",
        server_default=sa.text("uuid_generate_v4()"),
        existing_type=postgresql.UUID(as_uuid=True),
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.update_updated_at_column()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_users_updated_at') THEN
                CREATE TRIGGER update_users_updated_at
                BEFORE UPDATE ON public.users
                FOR EACH ROW
                EXECUTE PROCEDURE public.update_updated_at_column();
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_api_keys_updated_at') THEN
                CREATE TRIGGER update_api_keys_updated_at
                BEFORE UPDATE ON public.api_keys
                FOR EACH ROW
                EXECUTE PROCEDURE public.update_updated_at_column();
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_projects_updated_at') THEN
                CREATE TRIGGER update_projects_updated_at
                BEFORE UPDATE ON public.projects
                FOR EACH ROW
                EXECUTE PROCEDURE public.update_updated_at_column();
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_questions_updated_at') THEN
                CREATE TRIGGER update_questions_updated_at
                BEFORE UPDATE ON public.questions
                FOR EACH ROW
                EXECUTE PROCEDURE public.update_updated_at_column();
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_api_configs_updated_at') THEN
                CREATE TRIGGER update_api_configs_updated_at
                BEFORE UPDATE ON public.api_configs
                FOR EACH ROW
                EXECUTE PROCEDURE public.update_updated_at_column();
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_system_settings_updated_at') THEN
                CREATE TRIGGER update_system_settings_updated_at
                BEFORE UPDATE ON public.system_settings
                FOR EACH ROW
                EXECUTE PROCEDURE public.update_updated_at_column();
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_model_configs_updated_at') THEN
                CREATE TRIGGER update_model_configs_updated_at
                BEFORE UPDATE ON public.model_configs
                FOR EACH ROW
                EXECUTE PROCEDURE public.update_updated_at_column();
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_user_model_configs_updated_at') THEN
                CREATE TRIGGER update_user_model_configs_updated_at
                BEFORE UPDATE ON public.user_model_configs
                FOR EACH ROW
                EXECUTE PROCEDURE public.update_updated_at_column();
            END IF;
        END $$;
        """
    )
    op.alter_column(
        "projects",
        "settings",
        server_default=sa.text("'{}'::jsonb"),
        existing_type=postgresql.JSONB(),
    )
    op.alter_column(
        "datasets",
        "tags",
        server_default=sa.text("'[]'::jsonb"),
        existing_type=postgresql.JSONB(),
    )
    op.alter_column(
        "datasets",
        "dataset_metadata",
        server_default=sa.text("'{}'::jsonb"),
        existing_type=postgresql.JSONB(),
    )
    op.alter_column(
        "questions",
        "tags",
        server_default=sa.text("'[]'::jsonb"),
        existing_type=postgresql.JSONB(),
    )
    op.alter_column(
        "questions",
        "question_metadata",
        server_default=sa.text("'{}'::jsonb"),
        existing_type=postgresql.JSONB(),
    )
    op.alter_column(
        "performance_tests",
        "config",
        server_default=sa.text("'{}'::jsonb"),
        existing_type=postgresql.JSONB(),
    )
    op.alter_column(
        "performance_tests",
        "summary_metrics",
        server_default=sa.text("'{}'::jsonb"),
        existing_type=postgresql.JSONB(),
    )
    op.alter_column(
        "accuracy_test",
        "dimensions",
        server_default=sa.text("'[\"accuracy\"]'::jsonb"),
        existing_type=postgresql.JSONB(),
    )
    op.alter_column(
        "accuracy_test",
        "weights",
        server_default=sa.text("'{\"accuracy\": 1.0}'::jsonb"),
        existing_type=postgresql.JSONB(),
    )
    op.alter_column(
        "accuracy_test",
        "batch_settings",
        server_default=sa.text("'{\"batch_size\": 10, \"timeout_seconds\": 300}'::jsonb"),
        existing_type=postgresql.JSONB(),
    )


def downgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.alter_column(
        "reports",
        "id",
        server_default=sa.text("gen_random_uuid()"),
        existing_type=postgresql.UUID(as_uuid=True),
    )
    op.execute("DROP TRIGGER IF EXISTS update_user_model_configs_updated_at ON public.user_model_configs")
    op.execute("DROP TRIGGER IF EXISTS update_model_configs_updated_at ON public.model_configs")
    op.execute("DROP TRIGGER IF EXISTS update_system_settings_updated_at ON public.system_settings")
    op.execute("DROP TRIGGER IF EXISTS update_api_configs_updated_at ON public.api_configs")
    op.execute("DROP TRIGGER IF EXISTS update_questions_updated_at ON public.questions")
    op.execute("DROP TRIGGER IF EXISTS update_projects_updated_at ON public.projects")
    op.execute("DROP TRIGGER IF EXISTS update_api_keys_updated_at ON public.api_keys")
    op.execute("DROP TRIGGER IF EXISTS update_users_updated_at ON public.users")
    op.alter_column(
        "projects",
        "settings",
        server_default="{}",
        existing_type=postgresql.JSONB(),
    )
    op.alter_column(
        "datasets",
        "tags",
        server_default="[]",
        existing_type=postgresql.JSONB(),
    )
    op.alter_column(
        "datasets",
        "dataset_metadata",
        server_default="{}",
        existing_type=postgresql.JSONB(),
    )
    op.alter_column(
        "questions",
        "tags",
        server_default="[]",
        existing_type=postgresql.JSONB(),
    )
    op.alter_column(
        "questions",
        "question_metadata",
        server_default="{}",
        existing_type=postgresql.JSONB(),
    )
    op.alter_column(
        "performance_tests",
        "config",
        server_default="{}",
        existing_type=postgresql.JSONB(),
    )
    op.alter_column(
        "performance_tests",
        "summary_metrics",
        server_default="{}",
        existing_type=postgresql.JSONB(),
    )
    op.alter_column(
        "accuracy_test",
        "dimensions",
        server_default='["accuracy"]',
        existing_type=postgresql.JSONB(),
    )
    op.alter_column(
        "accuracy_test",
        "weights",
        server_default='{"accuracy": 1.0}',
        existing_type=postgresql.JSONB(),
    )
    op.alter_column(
        "accuracy_test",
        "batch_settings",
        server_default='{"batch_size": 10, "timeout_seconds": 300}',
        existing_type=postgresql.JSONB(),
    )
