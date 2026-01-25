from typing import Any, Dict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.project import Project
from app.models.dataset import Dataset
from app.models.question import Question


def get_system_statistics(db: Session) -> Dict[str, Any]:
    total_users = db.query(func.count(User.id)).scalar()
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
    admin_users = db.query(func.count(User.id)).filter(User.is_admin == True).scalar()

    total_projects = db.query(func.count(Project.id)).scalar()

    total_datasets = db.query(func.count(Dataset.id)).scalar()
    public_datasets = db.query(func.count(Dataset.id)).filter(Dataset.is_public == True).scalar()

    total_questions = db.query(func.count(Question.id)).scalar()

    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "admin": admin_users,
        },
        "projects": {
            "total": total_projects,
        },
        "datasets": {
            "total": total_datasets,
            "public": public_datasets,
        },
        "questions": {
            "total": total_questions,
        },
    }
