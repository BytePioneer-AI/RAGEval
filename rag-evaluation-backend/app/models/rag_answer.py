from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, UniqueConstraint, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, foreign
import uuid

from app.db.base import Base
from app.models.types import StringUUID

class RagAnswer(Base):
    __tablename__ = "rag_answers"

    id = Column(StringUUID, primary_key=True, default=uuid.uuid4)
    question_id = Column(StringUUID, nullable=False)  # SQL 中没有外键约束
    answer = Column(Text, nullable=False)
    collection_method = Column(String(20), nullable=False, default="api")  # api, manual_import

    sequence_number = Column(Integer, nullable=True)  # 在性能测试中的序号
    
    # 性能相关字段 - 使用 Numeric 匹配 SQL 定义
    first_response_time = Column(Numeric(10, 3))  # 首次响应时间(秒)
    total_response_time = Column(Numeric(10, 3))  # 总响应时间(秒)
    character_count = Column(Integer)  # 回答字符数
    characters_per_second = Column(Numeric(10, 2))  # 每秒生成字符数
    
    raw_response = Column(JSONB)  # 原始响应数据
    
    version = Column(String(50), nullable=True)  # 版本信息
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    performance_test_id = Column(StringUUID, ForeignKey("performance_tests.id", ondelete="SET NULL"), nullable=True)
    
    # 关系
    question = relationship(
        "Question",
        primaryjoin="foreign(RagAnswer.question_id) == Question.id",
        back_populates="rag_answers",
    )
    
    # 添加复合唯一约束
    __table_args__ = (
        UniqueConstraint('question_id', 'version', name='unique_question_version'),
    )

class ApiConfig(Base):
    """RAG系统API配置表"""
    __tablename__ = "api_configs"

    id = Column(StringUUID, primary_key=True, default=uuid.uuid4)
    project_id = Column(StringUUID, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    endpoint_url = Column(String(255), nullable=False)
    auth_type = Column(String(20), nullable=False, default="none")  # none, api_key, basic_auth
    api_key = Column(String(255))  # API密钥(如果使用)
    username = Column(String(100))  # 用户名(如果使用基本认证)
    password = Column(String(255))  # 密码(如果使用基本认证)
    request_format = Column(JSONB)  # 请求格式模板(JSON)
    response_path = Column(String(255))  # 从响应中提取答案的路径
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()) 
