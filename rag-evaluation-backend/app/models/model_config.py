from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
import uuid

from app.db.base import Base
from app.models.types import StringUUID


class ModelConfig(Base):
    __tablename__ = "model_configs"

    id = Column(StringUUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    provider = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    api_base = Column(String(255))
    default_params = Column(JSONB)
    is_public = Column(Boolean, default=False)
    created_by = Column(StringUUID, ForeignKey("users.id", ondelete="SET NULL"))
    scene = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
