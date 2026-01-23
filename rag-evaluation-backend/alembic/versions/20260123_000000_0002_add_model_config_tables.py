"""Add model config and user model config tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-01-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "model_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("api_base", sa.String(255)),
        sa.Column("default_params", postgresql.JSONB),
        sa.Column("is_public", sa.Boolean, server_default="false"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("scene", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_model_configs_provider", "model_configs", ["provider"])
    op.create_index("idx_model_configs_created_by", "model_configs", ["created_by"])

    op.create_table(
        "user_model_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("model_config_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("model_configs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("alias", sa.String(100)),
        sa.Column("key_encrypted", sa.Text, nullable=False),
        sa.Column("key_last4", sa.String(4), nullable=False),
        sa.Column("key_hash", sa.String(64)),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("rotated_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_user_model_configs_user_id", "user_model_configs", ["user_id"])
    op.create_index("idx_user_model_configs_model_config_id", "user_model_configs", ["model_config_id"])

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


def downgrade() -> None:
    op.drop_index("idx_api_key_audits_user_id", table_name="api_key_audits")
    op.drop_table("api_key_audits")
    op.drop_index("idx_user_model_configs_model_config_id", table_name="user_model_configs")
    op.drop_index("idx_user_model_configs_user_id", table_name="user_model_configs")
    op.drop_table("user_model_configs")
    op.drop_index("idx_model_configs_created_by", table_name="model_configs")
    op.drop_index("idx_model_configs_provider", table_name="model_configs")
    op.drop_table("model_configs")
