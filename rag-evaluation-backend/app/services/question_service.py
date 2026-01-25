from typing import List, Optional, Dict, Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.crud import question as crud_question
from app.crud import rag as crud_rag
from app.models.question import Question
from app.schemas.question import QuestionCreate, QuestionUpdate, QuestionBase, QuestionImportWithRagAnswer


def get_question(db: Session, question_id: str) -> Optional[Question]:
    return crud_question.get_question(db, question_id)


def get_questions_by_ids_for_project(
    db: Session,
    question_ids: List[str],
    project_id: str,
) -> List[Question]:
    return crud_question.get_questions_by_ids_and_project(
        db,
        question_ids=question_ids,
        project_id=project_id,
    )


def get_questions_by_project(
    db: Session,
    project_id: str,
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
) -> List[Question]:
    return crud_question.get_questions_by_project(
        db,
        project_id=project_id,
        skip=skip,
        limit=limit,
        category=category,
        difficulty=difficulty,
    )


def search_questions(
    db: Session,
    project_id: str,
    query: str,
    skip: int = 0,
    limit: int = 100,
) -> List[Question]:
    return crud_question.search_questions(
        db,
        project_id=project_id,
        query_text=query,
        skip=skip,
        limit=limit,
    )


def create_question(db: Session, obj_in: QuestionCreate) -> Question:
    obj_in_data = jsonable_encoder(obj_in)
    return crud_question.create_question(db, data=obj_in_data)


def create_question_with_rag_answer(
    db: Session,
    *,
    question_data: Dict[str, Any],
    rag_answer_data: Optional[Dict[str, Any]] = None,
) -> Question:
    return crud_question.create_question_with_rag_answer(
        db,
        question_data=question_data,
        rag_answer_data=rag_answer_data,
    )


def create_questions_batch(
    db: Session,
    dataset_id: str,
    questions: List[QuestionBase],
) -> List[Question]:
    return crud_question.create_questions_batch(db, dataset_id=dataset_id, questions=questions)


def create_questions_with_rag_answers(
    db: Session,
    *,
    dataset_id: str,
    questions_data: List[Dict[str, Any]],
) -> List[Question]:
    return crud_question.create_questions_with_rag_answers(
        db,
        dataset_id=dataset_id,
        questions_data=questions_data,
    )


def update_question(
    db: Session,
    db_obj: Question,
    obj_in: QuestionUpdate,
) -> Question:
    update_data = obj_in.dict(exclude_unset=True)
    return crud_question.update_question(db, db_obj=db_obj, update_data=update_data)


def delete_question(db: Session, question_id: str) -> bool:
    db_obj = get_question(db, question_id)
    if not db_obj:
        return False

    crud_question.delete_question(db, db_obj=db_obj)
    return True


def delete_questions_by_ids(
    db: Session,
    *,
    dataset_id: str,
    question_ids: List[str],
) -> int:
    return crud_question.delete_questions_by_ids(
        db,
        dataset_id=dataset_id,
        question_ids=question_ids,
    )


def list_dataset_questions_with_rag_answers(
    db: Session,
    *,
    dataset_id: str,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    version: Optional[str] = None,
) -> Dict[str, Any]:
    questions, total = crud_question.list_questions_by_dataset_with_filters(
        db,
        dataset_id=dataset_id,
        skip=skip,
        limit=limit,
        search=search,
        category=category,
        difficulty=difficulty,
        version=version,
    )

    question_ids = [str(question.id) for question in questions]
    rag_answers = crud_rag.list_rag_answers_by_question_ids(
        db,
        question_ids,
        version=version,
    )

    rag_answers_map: Dict[str, List[Dict[str, Any]]] = {}
    for rag_answer in rag_answers:
        rag_answers_map.setdefault(str(rag_answer.question_id), []).append({
            "id": str(rag_answer.id),
            "answer": rag_answer.answer,
            "collection_method": rag_answer.collection_method,
            "version": rag_answer.version,
            "first_response_time": rag_answer.first_response_time,
            "total_response_time": rag_answer.total_response_time,
            "character_count": rag_answer.character_count,
            "characters_per_second": rag_answer.characters_per_second,
            "created_at": rag_answer.created_at,
        })

    items = []
    for question in questions:
        question_id = str(question.id)
        items.append({
            "id": question_id,
            "dataset_id": str(question.dataset_id),
            "question_text": question.question_text,
            "standard_answer": question.standard_answer,
            "category": question.category,
            "difficulty": question.difficulty,
            "type": question.type,
            "tags": question.tags,
            "question_metadata": question.question_metadata,
            "created_at": question.created_at,
            "updated_at": question.updated_at,
            "rag_answers": rag_answers_map.get(question_id, []),
        })

    return {"items": items, "total": total}


def get_questions_by_dataset(
    db: Session,
    dataset_id: str,
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
) -> List[Question]:
    return crud_question.get_questions_by_dataset(
        db,
        dataset_id=dataset_id,
        skip=skip,
        limit=limit,
        category=category,
        difficulty=difficulty,
    )


def import_questions_with_rag_answers(
    db: Session,
    dataset_id: str,
    questions_data: List[QuestionImportWithRagAnswer],
) -> List[Question]:
    return crud_question.import_questions_with_rag_answers(
        db,
        dataset_id=dataset_id,
        questions_data=questions_data,
    )


def list_questions_for_export(
    db: Session,
    *,
    dataset_id: str,
    search: Optional[str] = None,
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
) -> List[Question]:
    return crud_question.list_questions_by_dataset_filtered(
        db,
        dataset_id=dataset_id,
        search=search,
        category=category,
        difficulty=difficulty,
    )
