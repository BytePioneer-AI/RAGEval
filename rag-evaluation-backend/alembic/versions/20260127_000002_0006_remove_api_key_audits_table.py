"""Remove redundant api_key_audits table

Revision ID: 0006
Revises: 0005
Create Date: 2026-01-27

api_key_audits 表是冗余的，user_model_configs 已经实现了用户与模型配置的多对多关系。
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("idx_api_key_audits_user_id", table_name="api_key_audits")
    op.drop_table("api_key_audits")


def downgrade() -> None:
    op.create_table(
        "api_key_audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("model_config_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("model_configs.id", ondelete="SET NULL")),
        sa.Column("user_model_config_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_model_configs.id", ondelete="SET NULL")),
        sa.Column("key_last4", sa.String(4)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_api_key_audits_user_id", "api_key_audits", ["user_id"])
