from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session

from app.models.project import Project, EvaluationDimension
from app.models.accuracy import AccuracyTest
from app.models.performance import PerformanceTest


def create_project(db: Session, *, data: Dict[str, Any], user_id: str) -> Project:
    db_obj = Project(**data, user_id=user_id)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def get_project(db: Session, project_id: str) -> Optional[Project]:
    return db.query(Project).filter(Project.id == project_id).first()


def list_projects_by_user(
    db: Session,
    *,
    user_id: str,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> List[Project]:
    query = db.query(Project).filter(Project.user_id == user_id)
    if status:
        query = query.filter(Project.status == status)
    if search:
        query = query.filter(Project.name.ilike(f"%{search}%"))
    return query.offset(skip).limit(limit).all()


def list_evaluation_dimensions(db: Session, project_id: str) -> List[EvaluationDimension]:
    return db.query(EvaluationDimension).filter(EvaluationDimension.project_id == project_id).all()


def update_project(db: Session, db_obj: Project, update_data: Dict[str, Any]) -> Project:
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_project(db: Session, db_obj: Project) -> None:
    db.delete(db_obj)
    db.commit()


def list_accuracy_tests_by_project(db: Session, project_id: str) -> List[AccuracyTest]:
    return db.query(AccuracyTest).filter(AccuracyTest.project_id == project_id).all()


def list_performance_tests_by_project(db: Session, project_id: str) -> List[PerformanceTest]:
    return db.query(PerformanceTest).filter(PerformanceTest.project_id == project_id).all()
