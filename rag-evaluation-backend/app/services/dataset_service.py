from typing import List, Optional, Dict, Any, Iterable

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.crud import dataset as crud_dataset
from app.models.dataset import Dataset, ProjectDataset
from app.models.question import Question
from app.schemas.dataset import DatasetCreate, DatasetUpdate


def serialize_dataset(
    dataset: Dataset,
    *,
    question_count: int = 0,
    current_user_id: Optional[str] = None,
    mask_user_id: bool = False,
    include_is_owner: bool = False,
) -> Dict[str, Any]:
    owner_id = str(dataset.user_id)
    is_owner = current_user_id is not None and str(current_user_id) == owner_id
    user_id = owner_id
    if mask_user_id and not is_owner:
        user_id = None

    result = {
        "id": str(dataset.id),
        "user_id": user_id,
        "name": dataset.name,
        "description": dataset.description,
        "is_public": dataset.is_public,
        "tags": dataset.tags or [],
        "dataset_metadata": dataset.dataset_metadata or {},
        "question_count": question_count,
        "created_at": dataset.created_at,
        "updated_at": dataset.updated_at,
    }

    if include_is_owner:
        result["is_owner"] = is_owner

    return result


def build_dataset_query(
    db: Session,
    *,
    user_id: str,
    include_public: bool = True,
    only_public: bool = False,
    only_private: bool = False,
    only_mine: bool = False,
    tags: Optional[List[str]] = None,
    search: Optional[str] = None,
) -> Any:
    return crud_dataset._build_dataset_query(
        db,
        user_id=user_id,
        include_public=include_public,
        only_public=only_public,
        only_private=only_private,
        only_mine=only_mine,
        tags=tags,
        search=search,
    )


def get_question_counts_by_dataset_ids(
    db: Session,
    dataset_ids: Iterable[str],
) -> Dict[str, int]:
    return crud_dataset.get_question_counts_by_dataset_ids(db, dataset_ids)


def create_dataset(db: Session, obj_in: DatasetCreate, user_id: str) -> Dataset:
    obj_in_data = jsonable_encoder(obj_in)
    return crud_dataset.create_dataset(db, data=obj_in_data, user_id=user_id)


def get_dataset(db: Session, dataset_id: str) -> Optional[Dataset]:
    return crud_dataset.get_dataset(db, dataset_id)


def get_datasets_by_user(
    db: Session,
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
    return crud_dataset.list_datasets_by_user(
        db,
        user_id=user_id,
        skip=skip,
        limit=limit,
        search=search,
        include_public=include_public,
        only_public=only_public,
        only_private=only_private,
        only_mine=only_mine,
        tags=tags,
    )


def get_public_datasets(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    tags: Optional[List[str]] = None,
) -> List[Dataset]:
    return crud_dataset.list_public_datasets(db, skip=skip, limit=limit, tags=tags)


def update_dataset(
    db: Session,
    dataset_id: str,
    obj_in: DatasetUpdate,
) -> Optional[Dataset]:
    db_obj = get_dataset(db, dataset_id)
    if not db_obj:
        return None

    update_data = obj_in.dict(exclude_unset=True)
    return crud_dataset.update_dataset(db, db_obj, update_data)


def delete_dataset(db: Session, dataset_id: str) -> bool:
    db_obj = get_dataset(db, dataset_id)
    if not db_obj:
        return False

    crud_dataset.delete_dataset(db, db_obj)
    return True


def get_dataset_with_stats(db: Session, dataset_id: str) -> Dict[str, Any]:
    dataset = get_dataset(db, dataset_id)
    if not dataset:
        return None

    question_count = crud_dataset.count_questions_for_dataset(db, dataset_id)
    projects = crud_dataset.list_projects_for_dataset(db, dataset_id)

    project_info = [
        {"id": str(project_id), "name": project_name}
        for project_id, project_name in projects
    ]

    return {
        "dataset": dataset,
        "question_count": question_count,
        "projects": project_info,
    }


def link_dataset_to_project(
    db: Session,
    project_id: str,
    dataset_id: str,
) -> Optional[ProjectDataset]:
    return crud_dataset.link_dataset_to_project(
        db,
        project_id=project_id,
        dataset_id=dataset_id,
    )


def unlink_dataset_from_project(
    db: Session,
    project_id: str,
    dataset_id: str,
) -> bool:
    return crud_dataset.unlink_dataset_from_project(
        db,
        project_id=project_id,
        dataset_id=dataset_id,
    )


def get_datasets_by_project(db: Session, project_id: str) -> List[Dataset]:
    return crud_dataset.list_datasets_by_project(db, project_id)


def get_questions_by_dataset(
    db: Session,
    dataset_id: str,
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
) -> List[Question]:
    return crud_dataset.list_questions_by_dataset(
        db,
        dataset_id=dataset_id,
        skip=skip,
        limit=limit,
        category=category,
        difficulty=difficulty,
    )


def copy_dataset(
    db: Session,
    source_dataset_id: str,
    user_id: str,
    new_name: Optional[str] = None,
) -> Optional[Dataset]:
    return crud_dataset.copy_dataset(
        db,
        source_dataset_id=source_dataset_id,
        user_id=user_id,
        new_name=new_name,
    )


def get_datasets_with_question_count(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[str] = None,
    is_public: Optional[bool] = None,
    tags: Optional[List[str]] = None,
    search: Optional[str] = None,
) -> List[Dict[str, Any]]:
    return crud_dataset.list_datasets_with_question_count(
        db,
        skip=skip,
        limit=limit,
        user_id=user_id,
        is_public=is_public,
        tags=tags,
        search=search,
    )


def get_project_datasets_with_question_count(
    db: Session,
    project_id: str,
) -> List[Dict[str, Any]]:
    return get_project_datasets_with_question_count_efficient(db, project_id)


def get_project_datasets_with_question_count_efficient(
    db: Session,
    project_id: str,
) -> List[Dict[str, Any]]:
    return crud_dataset.list_project_datasets_with_question_count_efficient(db, project_id)
