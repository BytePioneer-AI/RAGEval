from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.sql import func
import uuid

from app.db.base import Base
from app.models.types import StringUUID


class ApiKeyAudit(Base):
    __tablename__ = "api_key_audits"

    id = Column(StringUUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(StringUUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    model_config_id = Column(StringUUID, ForeignKey("model_configs.id", ondelete="SET NULL"))
    user_model_config_id = Column(StringUUID, ForeignKey("user_model_configs.id", ondelete="SET NULL"))
    key_last4 = Column(String(4))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
