from typing import List, Optional, Dict, Any, Tuple

from fastapi.encoders import jsonable_encoder
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from app.models.question import Question
from app.models.rag_answer import RagAnswer
from app.models.dataset import ProjectDataset
from app.schemas.question import QuestionBase, QuestionImportWithRagAnswer


def get_question(db: Session, question_id: str) -> Optional[Question]:
    return db.query(Question).filter(Question.id == question_id).first()


def get_questions_by_ids_and_project(
    db: Session,
    question_ids: List[str],
    project_id: str,
) -> List[Question]:
    if not question_ids:
        return []

    return db.query(Question).join(
        ProjectDataset, ProjectDataset.dataset_id == Question.dataset_id
    ).filter(
        ProjectDataset.project_id == project_id,
        Question.id.in_(question_ids),
    ).all()


def get_questions_by_ids_and_dataset(
    db: Session,
    question_ids: List[str],
    dataset_id: str,
) -> List[Question]:
    if not question_ids:
        return []

    return db.query(Question).filter(
        Question.dataset_id == dataset_id,
        Question.id.in_(question_ids),
    ).all()


def get_questions_by_project_direct(
    db: Session,
    *,
    project_id: str,
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
) -> List[Question]:
    query = db.query(Question).filter(Question.project_id == project_id)

    if category:
        query = query.filter(Question.category == category)

    if difficulty:
        query = query.filter(Question.difficulty == difficulty)

    return query.offset(skip).limit(limit).all()


def search_questions(
    db: Session,
    *,
    project_id: str,
    query_text: str,
    skip: int = 0,
    limit: int = 100,
) -> List[Question]:
    return db.query(Question).filter(
        Question.project_id == project_id,
        or_(
            Question.question_text.ilike(f"%{query_text}%"),
            Question.standard_answer.ilike(f"%{query_text}%"),
        ),
    ).offset(skip).limit(limit).all()


def create_question(db: Session, *, data: Dict[str, Any]) -> Question:
    db_obj = Question(**data)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def create_question_with_rag_answer(
    db: Session,
    *,
    question_data: Dict[str, Any],
    rag_answer_data: Optional[Dict[str, Any]] = None,
) -> Question:
    db_obj = Question(**question_data)
    db.add(db_obj)
    db.flush()

    if rag_answer_data:
        rag_answer = RagAnswer(question_id=db_obj.id, **rag_answer_data)
        db.add(rag_answer)

    db.commit()
    db.refresh(db_obj)
    return db_obj


def create_questions_batch(
    db: Session,
    *,
    dataset_id: str,
    questions: List[QuestionBase],
) -> List[Question]:
    db_objs = []

    for item in questions:
        obj_in_data = jsonable_encoder(item)
        db_obj = Question(**obj_in_data, dataset_id=dataset_id)
        db.add(db_obj)
        db_objs.append(db_obj)

    db.commit()

    for obj in db_objs:
        db.refresh(obj)

    return db_objs


def create_questions_with_rag_answers(
    db: Session,
    *,
    dataset_id: str,
    questions_data: List[Dict[str, Any]],
) -> List[Question]:
    created_questions = []

    for item in questions_data:
        payload = item.copy()
        rag_answer_data = payload.pop("rag_answer", None)

        question = Question(dataset_id=dataset_id, **payload)
        db.add(question)
        db.flush()

        if rag_answer_data:
            rag_answer = RagAnswer(question_id=question.id, **rag_answer_data)
            db.add(rag_answer)

        created_questions.append(question)

    db.commit()

    for question in created_questions:
        db.refresh(question)

    return created_questions


def update_question(
    db: Session,
    *,
    db_obj: Question,
    update_data: Dict[str, Any],
) -> Question:
    for field, value in update_data.items():
        setattr(db_obj, field, value)

    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_question(db: Session, *, db_obj: Question) -> None:
    db.delete(db_obj)
    db.commit()


def delete_questions_by_ids(
    db: Session,
    *,
    dataset_id: str,
    question_ids: List[str],
) -> int:
    questions = get_questions_by_ids_and_dataset(
        db,
        question_ids=question_ids,
        dataset_id=dataset_id,
    )
    if not questions:
        return 0

    for question in questions:
        db.delete(question)

    db.commit()
    return len(questions)


def get_questions_by_dataset(
    db: Session,
    *,
    dataset_id: str,
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
) -> List[Question]:
    query = db.query(Question).filter(Question.dataset_id == dataset_id)

    if category:
        query = query.filter(Question.category == category)

    if difficulty:
        query = query.filter(Question.difficulty == difficulty)

    return query.offset(skip).limit(limit).all()


def list_questions_by_dataset_with_filters(
    db: Session,
    *,
    dataset_id: str,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    version: Optional[str] = None,
) -> Tuple[List[Question], int]:
    query = db.query(Question)

    if version:
        query = query.join(
            RagAnswer,
            and_(
                RagAnswer.question_id == Question.id,
                RagAnswer.version == version,
            ),
        ).distinct()

    query = query.filter(Question.dataset_id == dataset_id)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Question.question_text.ilike(search_term),
                Question.standard_answer.ilike(search_term),
            )
        )

    if category:
        query = query.filter(Question.category == category)

    if difficulty:
        query = query.filter(Question.difficulty == difficulty)

    total = query.count()
    questions = query.offset(skip).limit(limit).all()
    return questions, total


def list_questions_by_dataset_filtered(
    db: Session,
    *,
    dataset_id: str,
    search: Optional[str] = None,
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
) -> List[Question]:
    query = db.query(Question).filter(Question.dataset_id == dataset_id)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Question.question_text.ilike(search_term),
                Question.standard_answer.ilike(search_term),
            )
        )

    if category:
        query = query.filter(Question.category == category)

    if difficulty:
        query = query.filter(Question.difficulty == difficulty)

    return query.all()


def get_questions_by_project(
    db: Session,
    *,
    project_id: str,
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
) -> List[Question]:
    dataset_ids = db.query(ProjectDataset.dataset_id).filter(
        ProjectDataset.project_id == project_id
    ).all()

    if not dataset_ids:
        return []

    dataset_ids = [d[0] for d in dataset_ids]

    query = db.query(Question).filter(Question.dataset_id.in_(dataset_ids))

    if category:
        query = query.filter(Question.category == category)

    if difficulty:
        query = query.filter(Question.difficulty == difficulty)

    return query.offset(skip).limit(limit).all()


def import_questions_with_rag_answers(
    db: Session,
    *,
    dataset_id: str,
    questions_data: List[QuestionImportWithRagAnswer],
) -> List[Question]:
    imported_questions = []

    for question_data in questions_data:
        rag_answer_text = question_data.rag_answer
        question_data_dict = question_data.dict(exclude={"rag_answer"})

        question = Question(dataset_id=dataset_id, **question_data_dict)
        db.add(question)
        db.flush()

        if rag_answer_text:
            rag_answer = RagAnswer(
                question_id=question.id,
                answer_text=rag_answer_text,
                collection_method="import",
                source_system="import",
                version="v1",
            )
            db.add(rag_answer)

        imported_questions.append(question)

    db.commit()

    for question in imported_questions:
        db.refresh(question)

    return imported_questions
