"""Add indexes for common list/query patterns

Revision ID: 0004
Revises: 0003
Create Date: 2026-01-27
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "idx_projects_user_id_created_at",
        "projects",
        ["user_id", "created_at"],
    )
    op.create_index(
        "idx_datasets_user_id_created_at",
        "datasets",
        ["user_id", "created_at"],
    )
    op.create_index(
        "idx_questions_dataset_id_created_at",
        "questions",
        ["dataset_id", "created_at"],
    )
    op.create_index(
        "idx_api_configs_project_id",
        "api_configs",
        ["project_id"],
    )
    op.create_index(
        "idx_accuracy_test_project_id_status",
        "accuracy_test",
        ["project_id", "status"],
    )
    op.create_index(
        "idx_accuracy_test_items_evaluation_id_status",
        "accuracy_test_items",
        ["evaluation_id", "status"],
    )
    op.create_index(
        "idx_reports_project_id_created_at",
        "reports",
        ["project_id", "created_at"],
    )
    op.create_index(
        "idx_project_datasets_dataset_id",
        "project_datasets",
        ["dataset_id"],
    )
    op.create_index(
        "idx_shared_projects_user_id",
        "shared_projects",
        ["user_id"],
    )
    op.create_index(
        "idx_performance_tests_project_id_created_at",
        "performance_tests",
        ["project_id", "created_at"],
    )
    op.create_index(
        "idx_rag_answers_question_id_created_at",
        "rag_answers",
        ["question_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_rag_answers_question_id_created_at", table_name="rag_answers")
    op.drop_index("idx_performance_tests_project_id_created_at", table_name="performance_tests")
    op.drop_index("idx_shared_projects_user_id", table_name="shared_projects")
    op.drop_index("idx_project_datasets_dataset_id", table_name="project_datasets")
    op.drop_index("idx_reports_project_id_created_at", table_name="reports")
    op.drop_index("idx_accuracy_test_items_evaluation_id_status", table_name="accuracy_test_items")
    op.drop_index("idx_accuracy_test_project_id_status", table_name="accuracy_test")
    op.drop_index("idx_api_configs_project_id", table_name="api_configs")
    op.drop_index("idx_questions_dataset_id_created_at", table_name="questions")
    op.drop_index("idx_datasets_user_id_created_at", table_name="datasets")
    op.drop_index("idx_projects_user_id_created_at", table_name="projects")
