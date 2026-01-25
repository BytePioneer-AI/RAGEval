from typing import List, Optional, Dict, Any, Iterable, Tuple

from sqlalchemy import func, or_, desc
from sqlalchemy.orm import Session

from app.models.dataset import Dataset, ProjectDataset
from app.models.question import Question
from app.models.project import Project


def _build_dataset_query(
    db: Session,
    *,
    user_id: str,
    include_public: bool = True,
    only_public: bool = False,
    only_private: bool = False,
    only_mine: bool = False,
    tags: Optional[List[str]] = None,
    search: Optional[str] = None,
):
    query = db.query(Dataset)

    if only_public:
        query = query.filter(Dataset.is_public == True)
    elif only_private:
        query = query.filter(
            Dataset.user_id == user_id,
            Dataset.is_public == False,
        )
    elif only_mine:
        query = query.filter(Dataset.user_id == user_id)
    elif include_public:
        query = query.filter(
            or_(
                Dataset.user_id == user_id,
                Dataset.is_public == True,
            )
        )
    else:
        query = query.filter(Dataset.user_id == user_id)

    if tags:
        for tag in tags:
            query = query.filter(Dataset.tags.contains([tag]))

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Dataset.name.ilike(search_term),
                Dataset.description.ilike(search_term),
            )
        )

    return query


def get_question_counts_by_dataset_ids(
    db: Session,
    dataset_ids: Iterable[str],
) -> Dict[str, int]:
    dataset_ids = list(dataset_ids)
    if not dataset_ids:
        return {}

    counts = (
        db.query(Question.dataset_id, func.count(Question.id))
        .filter(Question.dataset_id.in_(dataset_ids))
        .group_by(Question.dataset_id)
        .all()
    )

    return {str(dataset_id): count for dataset_id, count in counts}


def create_dataset(db: Session, *, data: Dict[str, Any], user_id: str) -> Dataset:
    db_obj = Dataset(**data, user_id=user_id)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def get_dataset(db: Session, dataset_id: str) -> Optional[Dataset]:
    return db.query(Dataset).filter(Dataset.id == dataset_id).first()


def list_all_datasets(db: Session) -> List[Dataset]:
    return db.query(Dataset).all()


def list_datasets_by_user(
    db: Session,
    *,
    user_id: str,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    include_public: bool = True,
    only_public: bool = False,
    only_private: bool = False,
    only_mine: bool = False,
    tags: Optional[List[str]] = None,
) -> List[Dataset]:
    query = _build_dataset_query(
        db,
        user_id=user_id,
        include_public=include_public,
        only_public=only_public,
        only_private=only_private,
        only_mine=only_mine,
        tags=tags,
        search=search,
    )

    query = query.order_by(Dataset.user_id == user_id, desc(Dataset.created_at))
    return query.offset(skip).limit(limit).all()


def list_public_datasets(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
    tags: Optional[List[str]] = None,
) -> List[Dataset]:
    query = db.query(Dataset).filter(Dataset.is_public == True)

    if tags:
        for tag in tags:
            query = query.filter(Dataset.tags.contains([tag]))

    return query.offset(skip).limit(limit).all()


def update_dataset(db: Session, db_obj: Dataset, update_data: Dict[str, Any]) -> Dataset:
    for field, value in update_data.items():
        setattr(db_obj, field, value)

    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_dataset(db: Session, db_obj: Dataset) -> None:
    db.delete(db_obj)
    db.commit()


def count_questions_for_dataset(db: Session, dataset_id: str) -> int:
    return db.query(func.count(Question.id)).filter(Question.dataset_id == dataset_id).scalar()


def list_projects_for_dataset(db: Session, dataset_id: str) -> List[Tuple[str, str]]:
    return (
        db.query(Project.id, Project.name)
        .join(ProjectDataset, ProjectDataset.project_id == Project.id)
        .filter(ProjectDataset.dataset_id == dataset_id)
        .all()
    )


def link_dataset_to_project(
    db: Session,
    *,
    project_id: str,
    dataset_id: str,
) -> ProjectDataset:
    existing = db.query(ProjectDataset).filter(
        ProjectDataset.project_id == project_id,
        ProjectDataset.dataset_id == dataset_id,
    ).first()

    if existing:
        return existing

    db_obj = ProjectDataset(project_id=project_id, dataset_id=dataset_id)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def get_project_dataset_link(
    db: Session,
    *,
    project_id: str,
    dataset_id: str,
) -> Optional[ProjectDataset]:
    return db.query(ProjectDataset).filter(
        ProjectDataset.project_id == project_id,
        ProjectDataset.dataset_id == dataset_id,
    ).first()


def unlink_dataset_from_project(
    db: Session,
    *,
    project_id: str,
    dataset_id: str,
) -> bool:
    db_obj = db.query(ProjectDataset).filter(
        ProjectDataset.project_id == project_id,
        ProjectDataset.dataset_id == dataset_id,
    ).first()

    if not db_obj:
        return False

    db.delete(db_obj)
    db.commit()
    return True


def count_project_links_for_dataset(db: Session, dataset_id: str) -> int:
    return db.query(func.count(ProjectDataset.id)).filter(
        ProjectDataset.dataset_id == dataset_id
    ).scalar()


def list_datasets_by_project(db: Session, project_id: str) -> List[Dataset]:
    dataset_ids = db.query(ProjectDataset.dataset_id).filter(
        ProjectDataset.project_id == project_id
    ).all()

    if not dataset_ids:
        return []

    dataset_ids = [d[0] for d in dataset_ids]

    return db.query(Dataset).filter(Dataset.id.in_(dataset_ids)).all()


def list_questions_by_dataset(
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


def copy_dataset(
    db: Session,
    *,
    source_dataset_id: str,
    user_id: str,
    new_name: Optional[str] = None,
) -> Optional[Dataset]:
    source_dataset = get_dataset(db, dataset_id=source_dataset_id)
    if not source_dataset:
        return None

    if not source_dataset.is_public and str(source_dataset.user_id) != user_id:
        return None

    new_dataset = Dataset(
        user_id=user_id,
        name=new_name or f"{source_dataset.name} (复制)",
        description=source_dataset.description,
        is_public=False,
        tags=source_dataset.tags,
        dataset_metadata=source_dataset.dataset_metadata,
    )

    db.add(new_dataset)
    db.commit()
    db.refresh(new_dataset)

    questions = db.query(Question).filter(
        Question.dataset_id == source_dataset_id
    ).all()

    for question in questions:
        new_question = Question(
            dataset_id=new_dataset.id,
            question_text=question.question_text,
            standard_answer=question.standard_answer,
            category=question.category,
            difficulty=question.difficulty,
            type=question.type,
            tags=question.tags,
            question_metadata=question.question_metadata,
        )
        db.add(new_question)

    db.commit()

    return new_dataset


def list_datasets_with_question_count(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[str] = None,
    is_public: Optional[bool] = None,
    tags: Optional[List[str]] = None,
    search: Optional[str] = None,
) -> List[Dict[str, Any]]:
    dataset_query = db.query(Dataset)

    if user_id is not None:
        dataset_query = dataset_query.filter(
            or_(Dataset.user_id == user_id, Dataset.is_public == True)
        )

    if is_public is not None:
        dataset_query = dataset_query.filter(Dataset.is_public == is_public)

    if tags:
        for tag in tags:
            dataset_query = dataset_query.filter(Dataset.tags.contains([tag]))

    if search:
        search_term = f"%{search}%"
        dataset_query = dataset_query.filter(
            or_(
                Dataset.name.ilike(search_term),
                Dataset.description.ilike(search_term),
            )
        )

    if user_id:
        dataset_query = dataset_query.order_by(Dataset.user_id == user_id, desc(Dataset.created_at))
    else:
        dataset_query = dataset_query.order_by(desc(Dataset.created_at))

    datasets = dataset_query.offset(skip).limit(limit).subquery()

    counts_subq = (
        db.query(
            Question.dataset_id.label("dataset_id"),
            func.count(Question.id).label("question_count"),
        )
        .group_by(Question.dataset_id)
        .subquery()
    )

    rows = (
        db.query(Dataset, counts_subq.c.question_count)
        .join(datasets, Dataset.id == datasets.c.id)
        .outerjoin(counts_subq, Dataset.id == counts_subq.c.dataset_id)
        .all()
    )

    return [
        {"dataset": dataset, "question_count": count or 0}
        for dataset, count in rows
    ]


def list_project_datasets_with_question_count_efficient(
    db: Session,
    project_id: str,
) -> List[Dict[str, Any]]:
    dataset_ids = db.query(ProjectDataset.dataset_id).filter(
        ProjectDataset.project_id == project_id
    ).all()

    if not dataset_ids:
        return []

    dataset_ids = [d[0] for d in dataset_ids]

    subq = db.query(
        Question.dataset_id.label("dataset_id"),
        func.count(Question.id).label("question_count"),
    ).group_by(Question.dataset_id).subquery()

    query = db.query(
        Dataset,
        subq.c.question_count,
    ).outerjoin(
        subq, Dataset.id == subq.c.dataset_id
    ).filter(
        Dataset.id.in_(dataset_ids)
    )

    result = []
    for dataset, count in query.all():
        result.append({
            "dataset": dataset,
            "question_count": count or 0,
        })

    return result
