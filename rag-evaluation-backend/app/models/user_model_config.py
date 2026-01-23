from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
import uuid

from app.db.base import Base
from app.models.types import StringUUID


class UserModelConfig(Base):
    __tablename__ = "user_model_configs"

    id = Column(StringUUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(StringUUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    model_config_id = Column(StringUUID, ForeignKey("model_configs.id", ondelete="CASCADE"), nullable=False)
    alias = Column(String(100))
    key_encrypted = Column(Text, nullable=False)
    key_last4 = Column(String(4), nullable=False)
    key_hash = Column(String(64))
    is_active = Column(Boolean, default=True)
    rotated_at = Column(DateTime(timezone=True))
    revoked_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
