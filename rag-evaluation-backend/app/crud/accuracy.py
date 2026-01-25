from typing import List, Optional, Dict, Any, Tuple

from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.models.accuracy import AccuracyTest, AccuracyTestItem, AccuracyHumanAssignment
from app.models.question import Question
from app.models.rag_answer import RagAnswer


def create_accuracy_test(db: Session, *, data: Dict[str, Any]) -> AccuracyTest:
    db_obj = AccuracyTest(**data)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def save_accuracy_test(db: Session, test: AccuracyTest) -> AccuracyTest:
    db.add(test)
    db.commit()
    db.refresh(test)
    return test


def list_questions_by_dataset(db: Session, dataset_id: str) -> List[Question]:
    return db.query(Question).filter(Question.dataset_id == dataset_id).all()


def get_latest_rag_answer(
    db: Session,
    *,
    question_id: str,
    version: Optional[str] = None,
) -> Optional[RagAnswer]:
    query = db.query(RagAnswer).filter(RagAnswer.question_id == question_id)
    if version:
        query = query.filter(RagAnswer.version == version)
    return query.order_by(RagAnswer.created_at.desc()).first()


def bulk_save_accuracy_items(db: Session, items: List[AccuracyTestItem]) -> None:
    if items:
        db.bulk_save_objects(items)
    db.commit()


def list_accuracy_tests_by_project(db: Session, project_id: str) -> List[AccuracyTest]:
    return db.query(AccuracyTest).filter(
        AccuracyTest.project_id == project_id
    ).order_by(AccuracyTest.created_at.desc()).all()


def get_accuracy_test(db: Session, test_id: str) -> Optional[AccuracyTest]:
    return db.query(AccuracyTest).filter(AccuracyTest.id == test_id).first()


def get_accuracy_test_items(
    db: Session,
    *,
    test_id: str,
    limit: int,
    offset: int,
    status: Optional[str] = None,
    score: Optional[float] = None,
) -> Tuple[List[Tuple[AccuracyTestItem, str, str, str]], int]:
    query = db.query(
        AccuracyTestItem,
        Question.question_text.label("question_content"),
        Question.standard_answer.label("reference_answer"),
        RagAnswer.answer.label("rag_answer_content"),
    ).join(
        Question, AccuracyTestItem.question_id == Question.id
    ).join(
        RagAnswer, AccuracyTestItem.rag_answer_id == RagAnswer.id
    ).filter(
        AccuracyTestItem.evaluation_id == test_id
    )

    if status:
        query = query.filter(AccuracyTestItem.status == status)

    if score is not None:
        query = query.filter(AccuracyTestItem.final_score == score)

    total_count = query.count()
    items = query.order_by(
        AccuracyTestItem.sequence_number.asc()
    ).offset(offset).limit(limit).all()

    return items, total_count


def get_accuracy_test_item_by_question(
    db: Session,
    *,
    test_id: str,
    question_id: str,
) -> Optional[AccuracyTestItem]:
    return db.query(AccuracyTestItem).filter(
        AccuracyTestItem.question_id == question_id,
        AccuracyTestItem.evaluation_id == test_id,
    ).first()


def save_accuracy_test_item(db: Session, item: AccuracyTestItem) -> AccuracyTestItem:
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def list_accuracy_items_for_results(db: Session, test_id: str) -> List[AccuracyTestItem]:
    return db.query(AccuracyTestItem).filter(
        AccuracyTestItem.evaluation_id == test_id,
        AccuracyTestItem.status.in_(["ai_completed", "human_completed", "both_completed"]),
    ).all()


def get_accuracy_test_stats(db: Session, test_id: str) -> Tuple[int, int, int]:
    stats = db.query(
        func.count(AccuracyTestItem.id).label("total"),
        func.sum(
            case(
                (AccuracyTestItem.status.in_(["ai_completed", "human_completed", "both_completed"]), 1),
                else_=0,
            )
        ).label("processed"),
        func.sum(
            case(
                (AccuracyTestItem.status == "failed", 1),
                else_=0,
            )
        ).label("failed"),
    ).filter(
        AccuracyTestItem.evaluation_id == test_id
    ).first()

    if not stats:
        return 0, 0, 0

    return stats.total or 0, stats.processed or 0, stats.failed or 0


def list_accuracy_items_by_status(
    db: Session,
    *,
    test_id: str,
    statuses: List[str],
    limit: Optional[int] = None,
) -> List[AccuracyTestItem]:
    query = db.query(AccuracyTestItem).filter(
        AccuracyTestItem.evaluation_id == test_id,
        AccuracyTestItem.status.in_(statuses),
    )
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def create_human_assignment(db: Session, *, data: Dict[str, Any]) -> AccuracyHumanAssignment:
    assignment = AccuracyHumanAssignment(**data)
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def list_human_assignments(db: Session, test_id: str) -> List[AccuracyHumanAssignment]:
    return db.query(AccuracyHumanAssignment).filter(
        AccuracyHumanAssignment.evaluation_id == test_id
    ).order_by(AccuracyHumanAssignment.assigned_at.desc()).all()


def list_running_tests(db: Session, project_id: str) -> List[AccuracyTest]:
    return db.query(AccuracyTest).filter(
        AccuracyTest.project_id == project_id,
        AccuracyTest.status == "running",
    ).all()


def delete_items_by_status(db: Session, *, test_id: str, statuses: List[str]) -> None:
    db.query(AccuracyTestItem).filter(
        AccuracyTestItem.evaluation_id == test_id,
        AccuracyTestItem.status.in_(statuses),
    ).delete()
    db.commit()


def rollback(db: Session) -> None:
    db.rollback()
