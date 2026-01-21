from sqlalchemy import Column, String, Text, DateTime, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
import uuid

from app.db.base import Base
from app.models.types import StringUUID

class PerformanceTest(Base):
    """RAG系统性能测试表"""
    __tablename__ = "performance_tests"

    id = Column(StringUUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    project_id = Column(StringUUID, nullable=False)  # SQL 中没有外键约束
    dataset_id = Column(StringUUID, nullable=True)  # SQL 中没有外键约束
    description = Column(Text)
    concurrency = Column(Integer, nullable=False)
    version = Column(String(50))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # status 有 CHECK 约束: created, running, completed, failed, terminated
    status = Column(String(20), default="created", nullable=False)
    config = Column(JSONB, default={}, nullable=False)
    
    total_questions = Column(Integer, default=0, nullable=False)
    processed_questions = Column(Integer, default=0, nullable=False)
    success_questions = Column(Integer, default=0, nullable=False)
    failed_questions = Column(Integer, default=0, nullable=False)
    
    summary_metrics = Column(JSONB, default={}, nullable=False)
    rag_config = Column(String(200), nullable=True)