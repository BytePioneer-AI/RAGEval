from typing import List, Optional, Dict, Any, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.rag_answer import RagAnswer, ApiConfig
from app.models.question import Question
from app.models.dataset import ProjectDataset


def get_questions_by_ids(db: Session, question_ids: List[str]) -> List[Question]:
    return db.query(Question).filter(Question.id.in_(question_ids)).all()


def get_question(db: Session, question_id: str) -> Optional[Question]:
    return db.query(Question).filter(Question.id == question_id).first()


def create_rag_answer(db: Session, *, data: Dict[str, Any]) -> RagAnswer:
    db_obj = RagAnswer(**data)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def list_answers_by_question(
    db: Session,
    question_id: str,
    version: Optional[str] = None,
) -> List[RagAnswer]:
    query = db.query(RagAnswer).filter(RagAnswer.question_id == question_id)
    if version:
        query = query.filter(RagAnswer.version == version)
    return query.all()


def list_answers_by_project(
    db: Session,
    *,
    project_id: str,
    skip: int = 0,
    limit: int = 100,
) -> List[RagAnswer]:
    question_ids = db.query(Question.id).join(
        ProjectDataset, ProjectDataset.dataset_id == Question.dataset_id
    ).filter(
        ProjectDataset.project_id == project_id
    ).all()
    question_ids = [q[0] for q in question_ids]

    return db.query(RagAnswer).filter(
        RagAnswer.question_id.in_(question_ids)
    ).offset(skip).limit(limit).all()


def get_rag_answer(db: Session, answer_id: str) -> Optional[RagAnswer]:
    return db.query(RagAnswer).filter(RagAnswer.id == answer_id).first()


def get_rag_answer_by_question_and_version(
    db: Session,
    question_id: str,
    version: str,
) -> Optional[RagAnswer]:
    return db.query(RagAnswer).filter(
        RagAnswer.question_id == question_id,
        RagAnswer.version == version,
    ).first()


def list_rag_answers_by_question_ids(
    db: Session,
    question_ids: List[str],
    version: Optional[str] = None,
) -> List[RagAnswer]:
    if not question_ids:
        return []

    query = db.query(RagAnswer).filter(RagAnswer.question_id.in_(question_ids))
    if version:
        query = query.filter(RagAnswer.version == version)
    return query.all()


def delete_rag_answer(db: Session, answer_id: str) -> bool:
    db_obj = db.query(RagAnswer).filter(RagAnswer.id == answer_id).first()
    if not db_obj:
        return False
    db.delete(db_obj)
    db.commit()
    return True


def update_rag_answer(
    db: Session,
    db_obj: RagAnswer,
    update_data: Dict[str, Any],
) -> RagAnswer:
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def save_api_config(db: Session, *, data: Dict[str, Any]) -> ApiConfig:
    db_obj = ApiConfig(**data)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def get_dataset_version_counts(db: Session, dataset_id: str) -> List[Tuple[Optional[str], int]]:
    return db.query(
        RagAnswer.version,
        func.count(RagAnswer.id).label("count"),
    ).join(
        Question, RagAnswer.question_id == Question.id
    ).filter(
        Question.dataset_id == dataset_id,
        RagAnswer.version.isnot(None),
    ).group_by(
        RagAnswer.version
    ).all()
