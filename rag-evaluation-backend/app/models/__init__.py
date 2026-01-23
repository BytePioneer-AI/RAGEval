"""Model import hub to register all SQLAlchemy models for Alembic."""

from app.models.user import User
from app.models.api_key import ApiKey
from app.models.model_config import ModelConfig
from app.models.user_model_config import UserModelConfig
from app.models.api_key_audit import ApiKeyAudit
from app.models.project import Project, EvaluationDimension
from app.models.dataset import Dataset, ProjectDataset
from app.models.question import Question
from app.models.rag_answer import RagAnswer, ApiConfig
from app.models.accuracy import AccuracyTest, AccuracyTestItem, AccuracyHumanAssignment
from app.models.performance import PerformanceTest
from app.models.report import Report

__all__ = [
    "User",
    "ApiKey",
    "Project",
    "EvaluationDimension",
    "Dataset",
    "ProjectDataset",
    "Question",
    "RagAnswer",
    "ApiConfig",
    "ModelConfig",
    "UserModelConfig",
    "ApiKeyAudit",
    "AccuracyTest",
    "AccuracyTestItem",
    "AccuracyHumanAssignment",
    "PerformanceTest",
    "Report",
]
