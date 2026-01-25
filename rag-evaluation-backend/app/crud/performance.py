from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.performance import PerformanceTest
from app.models.rag_answer import RagAnswer
from app.models.question import Question


def get_performance_test(db: Session, test_id: str) -> Optional[PerformanceTest]:
    return db.query(PerformanceTest).filter(PerformanceTest.id == test_id).first()


def list_performance_tests(db: Session, skip: int = 0, limit: int = 100) -> List[PerformanceTest]:
    return db.query(PerformanceTest).offset(skip).limit(limit).all()


def list_performance_tests_by_project(db: Session, project_id: str) -> List[PerformanceTest]:
    return db.query(PerformanceTest).filter(
        PerformanceTest.project_id == project_id
    ).order_by(PerformanceTest.created_at.desc()).all()


def count_performance_tests_for_project_dataset(
    db: Session,
    *,
    project_id: str,
    dataset_id: str,
) -> int:
    return db.query(func.count(PerformanceTest.id)).filter(
        PerformanceTest.project_id == project_id,
        PerformanceTest.dataset_id == dataset_id,
    ).scalar()


def create_performance_test(db: Session, *, data: Dict[str, Any]) -> PerformanceTest:
    db_obj = PerformanceTest(**data)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_performance_test(
    db: Session,
    *,
    db_obj: PerformanceTest,
    update_data: Dict[str, Any],
) -> PerformanceTest:
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def list_rag_answers_by_test(db: Session, performance_test_id: str) -> List[RagAnswer]:
    return db.query(RagAnswer).filter(
        RagAnswer.performance_test_id == performance_test_id
    ).all()


def list_rag_answers_by_test_ordered(db: Session, performance_test_id: str) -> List[RagAnswer]:
    return db.query(RagAnswer).filter(
        RagAnswer.performance_test_id == performance_test_id
    ).order_by(RagAnswer.sequence_number).all()


def get_qa_pairs(
    db: Session,
    *,
    performance_test_id: str,
    skip: int = 0,
    limit: int = 50,
) -> Dict[str, Any]:
    query_base = (
        db.query(
            RagAnswer.id,
            RagAnswer.question_id,
            RagAnswer.answer,
            RagAnswer.total_response_time,
            RagAnswer.first_response_time,
            RagAnswer.sequence_number,
            Question.question_text.label("question_content"),
        )
        .join(Question, RagAnswer.question_id == Question.id)
        .filter(RagAnswer.performance_test_id == performance_test_id)
        .order_by(RagAnswer.sequence_number)
    )

    total = query_base.count()
    results = query_base.offset(skip).limit(limit).all()

    items = []
    for i, row in enumerate(results):
        items.append({
            "id": row.id,
            "question_id": row.question_id,
            "question_content": row.question_content,
            "answer": row.answer,
            "total_response_time": row.total_response_time,
            "first_response_time": row.first_response_time,
            "sequence_number": row.sequence_number if row.sequence_number is not None else i + 1 + skip,
        })

    page = skip // limit + 1 if limit > 0 else 1
    pages = (total + limit - 1) // limit if total > 0 else 1

    return {
        "items": items,
        "total": total,
        "page": page,
        "size": limit,
        "pages": pages,
    }
