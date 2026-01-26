"""Remove redundant api_keys table

Revision ID: 0005
Revises: 0004
Create Date: 2026-01-27

api_keys 表功能与 user_model_configs 表重叠，后者设计更完善（加密存储、hash去重、last4展示等），
因此删除冗余的 api_keys 表。
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 删除 api_keys 表的触发器
    op.execute("DROP TRIGGER IF EXISTS update_api_keys_updated_at ON public.api_keys")
    
    # 删除 api_keys 表
    op.drop_table("api_keys")


def downgrade() -> None:
    # 重建 api_keys 表
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("key", sa.String(100), unique=True, nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    
    # 重建触发器
    op.execute("""
        CREATE TRIGGER update_api_keys_updated_at
        BEFORE UPDATE ON public.api_keys
        FOR EACH ROW
        EXECUTE PROCEDURE public.update_updated_at_column();
    """)
