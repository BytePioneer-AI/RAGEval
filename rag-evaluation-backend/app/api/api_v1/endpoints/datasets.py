from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_active_admin, get_db
from app.models.user import User
from app.schemas.dataset import (
    DatasetCreate,
    DatasetUpdate,
    DatasetOut,
    DatasetDetail,
    BatchLinkDatasets
)
from app.schemas.question import QuestionOut
from app.schemas.common import PaginatedResponse

from app.services.dataset_service import (
    create_dataset,
    get_dataset,
    list_all_datasets_with_counts,
    list_datasets_page,
    list_public_datasets_page,
    serialize_dataset,
    update_dataset,
    delete_dataset,
    count_questions_for_dataset,
    get_dataset_with_stats,
    link_dataset_to_project,
    unlink_dataset_from_project,
    count_project_links_for_dataset,
    get_project_dataset_link,
    get_questions_by_dataset,
    copy_dataset,
    count_accuracy_tests_for_project_dataset,
    count_performance_tests_for_project_dataset,
)
from app.services.project_service import get_project

router = APIRouter()

@router.get("/admin", response_model=List[DatasetOut])
def read_all_datasets(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
) -> Any:
    """
    获取所有数据集（仅管理员可访问）
    """
    # 查询所有数据集
    return list_all_datasets_with_counts(db)

@router.post("", response_model=DatasetOut)
def create_dataset_api(
    *,
    db: Session = Depends(get_db),
    dataset_in: DatasetCreate,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    创建数据集
    """
    dataset = create_dataset(db, obj_in=dataset_in, user_id=str(current_user.id))

    # 手动转换返回值，确保UUID被转换为字符串
    return serialize_dataset(dataset, question_count=0, mask_user_id=False)

@router.get("", response_model=PaginatedResponse[DatasetOut])
def read_datasets(
    *,
    db: Session = Depends(get_db),
    page: int = Query(1, gt=0),
    size: int = Query(10, gt=0, le=100),
    search: Optional[str] = None,
    filter_type: Optional[str] = Query("all", description="筛选类型: all/my/public/private"),
    tags: Optional[str] = Query(None, description="标签，多个用逗号分隔"),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    获取数据集列表，支持多种筛选条件
    """
    skip = (page - 1) * size

    # 处理标签
    tag_list = tags.split(",") if tags else None

    # 设置公开和所有者筛选
    include_public = True
    only_public = False
    only_private = False
    only_mine = False

    if filter_type == "my":
        include_public = False  # 只看我的数据集
        only_mine = True
    elif filter_type == "public":
        only_public = True  # 只看公开数据集
    elif filter_type == "private":
        only_private = True  # 只看私有数据集
        include_public = False

    # 获取数据集列表
    result = list_datasets_page(
        db,
        user_id=str(current_user.id),
        skip=skip,
        limit=size,
        include_public=include_public,
        only_public=only_public,
        only_private=only_private,
        only_mine=only_mine,
        tags=tag_list,
        search=search,
    )

    total = result["total"]
    pages = (total + size - 1) // size if total > 0 else 1

    return {
        "items": result["items"],
        "total": total,
        "page": page,
        "size": size,
        "pages": pages
    }

@router.get("/public", response_model=PaginatedResponse[DatasetOut])
def read_public_datasets(
    *,
    db: Session = Depends(get_db),
    page: int = Query(1, gt=0),
    size: int = Query(12, gt=0, le=100),
    tags: Optional[str] = Query(None, description="标签，多个用逗号分隔"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    获取公开数据集
    """
    tag_list = tags.split(",") if tags else None

    # 创建基础查询
    result = list_public_datasets_page(
        db,
        user_id=str(current_user.id),
        skip=(page - 1) * size,
        limit=size,
        tags=tag_list,
        search=search,
    )

    total = result["total"]
    pages = (total + size - 1) // size if total > 0 else 1

    return {
        "items": result["items"],
        "total": total,
        "page": page,
        "size": size,
        "pages": pages
    }



@router.get("/{dataset_id}", response_model=DatasetDetail)
def read_dataset(
    *,
    db: Session = Depends(get_db),
    dataset_id: str,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    获取数据集详情
    """
    dataset = get_dataset(db, dataset_id=dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集未找到")

    # 检查访问权限
    if not dataset.is_public and str(dataset.user_id) != str(current_user.id) and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权访问此数据集")

    result = get_dataset_with_stats(db, dataset_id)

    # 将result转换为schema需要的格式，明确转换UUID为字符串
    response = serialize_dataset(
        result["dataset"],
        question_count=result["question_count"],
        mask_user_id=False,
    )
    response["projects"] = result["projects"]

    return response

@router.put("/{dataset_id}", response_model=DatasetOut)
def update_dataset_api(
    *,
    db: Session = Depends(get_db),
    dataset_id: str,
    dataset_in: DatasetUpdate,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    更新数据集
    """
    dataset = get_dataset(db, dataset_id=dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集未找到")

    # 检查权限
    if str(dataset.user_id) != str(current_user.id) and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权修改此数据集")

    dataset = update_dataset(db, dataset_id=dataset_id, obj_in=dataset_in)

    # ???????
    question_count = count_questions_for_dataset(db, dataset_id=str(dataset.id))

    # 手动转换返回值，确保UUID被转换为字符串
    return serialize_dataset(dataset, question_count=question_count, mask_user_id=False)

@router.delete("/{dataset_id}")
def delete_dataset_api(
    *,
    db: Session = Depends(get_db),
    dataset_id: str,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    删除数据集
    """
    dataset = get_dataset(db, dataset_id=dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集未找到")

    # 检查删除权限
    if str(dataset.user_id) != str(current_user.id) and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权删除此数据集")

    # 检查是否有项目正在使用此数据集
    project_links = count_project_links_for_dataset(db, dataset_id=dataset_id)

    if project_links > 0:
        raise HTTPException(status_code=400, detail="数据集正在被项目使用，无法删除")

    delete_dataset(db, dataset_id=dataset_id)
    return {"detail": "数据集已删除"}



@router.post("/link/{project_id}", response_model=dict)
def link_datasets_to_project(
    *,
    db: Session = Depends(get_db),
    project_id: str,
    link_data: BatchLinkDatasets,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    批量关联数据集到项目
    """
    # 检查项目权限
    project = get_project(db, project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目未找到")

    if str(project.user_id) != str(current_user.id) and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权操作此项目")

    # 验证所有数据集是否存在，以及用户是否有权限访问
    datasets = []
    for dataset_id in link_data.dataset_ids:
        dataset = get_dataset(db, dataset_id=dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail=f"数据集 {dataset_id} 未找到")

        if not dataset.is_public and str(dataset.user_id) != str(current_user.id) and not current_user.is_admin:
            raise HTTPException(status_code=403, detail=f"无权访问数据集 {dataset_id}")

        datasets.append(dataset)

    # 关联数据集到项目
    added_datasets = []
    for dataset in datasets:
        link = link_dataset_to_project(db, project_id=project_id, dataset_id=str(dataset.id))
        added_datasets.append({
            "id": str(dataset.id),
            "name": dataset.name
        })

    return {
        "success": True,
        "added_datasets": added_datasets
    }

@router.delete("/unlink/{project_id}/{dataset_id}")
def unlink_dataset_from_project_api(
    *,
    db: Session = Depends(get_db),
    project_id: str,
    dataset_id: str,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    从项目中移除数据集关联
    """
    # 检查项目权限
    project = get_project(db, project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目未找到")

    if str(project.user_id) != str(current_user.id) and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权操作此项目")

    # 检查关联是否存在
    link = get_project_dataset_link(db, project_id=project_id, dataset_id=dataset_id)

    if not link:
        raise HTTPException(status_code=404, detail="项目未关联此数据集")

    # 检查是否有使用此数据集的精度评测结果
    accuracy_tests = count_accuracy_tests_for_project_dataset(
        db,
        project_id=project_id,
        dataset_id=dataset_id,
    )

    if accuracy_tests > 0:
        raise HTTPException(
            status_code=400,
            detail="该数据集已被用于精度评测，无法移除。"
        )

    # 检查是否有使用此数据集的性能评测结果
    performance_tests = count_performance_tests_for_project_dataset(
        db,
        project_id=project_id,
        dataset_id=dataset_id,
    )

    if performance_tests > 0:
        raise HTTPException(
            status_code=400,
            detail="该数据集已被用于性能评测，无法移除。"
        )

    unlink_dataset_from_project(db, project_id=project_id, dataset_id=dataset_id)
    return {"detail": "数据集已从项目中移除"}

@router.get("/{dataset_id}/questions", response_model=List[QuestionOut])
def read_dataset_questions(
    *,
    db: Session = Depends(get_db),
    dataset_id: str,
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    获取数据集中的问题列表
    """
    dataset = get_dataset(db, dataset_id=dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集未找到")

    # 检查访问权限
    if not dataset.is_public and str(dataset.user_id) != str(current_user.id) and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权访问此数据集")

    questions = get_questions_by_dataset(
        db,
        dataset_id=dataset_id,
        skip=skip,
        limit=limit,
        category=category,
        difficulty=difficulty
    )

    # 转换UUID为字符串
    result = []
    for question in questions:
        question_dict = {
            "id": str(question.id),
            "dataset_id": str(question.dataset_id),
            "question_text": question.question_text,
            "standard_answer": question.standard_answer,
            "category": question.category,
            "difficulty": question.difficulty,
            "type": question.type,
            "tags": question.tags,
            "question_metadata": question.question_metadata,
            "created_at": question.created_at,
            "updated_at": question.updated_at
        }
        result.append(question_dict)

    return result

@router.post("/{dataset_id}/copy", response_model=DatasetOut)
def copy_dataset_api(
    *,
    db: Session = Depends(get_db),
    dataset_id: str,
    name: Optional[str] = Query(None, description="新数据集名称"),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    复制公开数据集到当前用户的私人数据集
    """
    # 检查源数据集
    source_dataset = get_dataset(db, dataset_id=dataset_id)
    if not source_dataset:
        raise HTTPException(status_code=404, detail="数据集未找到")

    # 检查权限 - 如果数据集不是公开的且不属于当前用户，则拒绝访问
    if not source_dataset.is_public and str(source_dataset.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="无权复制此数据集")

    # 执行复制
    new_dataset = copy_dataset(db, source_dataset_id=dataset_id, user_id=str(current_user.id), new_name=name)

    if not new_dataset:
        raise HTTPException(status_code=500, detail="复制数据集失败")

    # 获取问题数量
    question_count = count_questions_for_dataset(db, dataset_id=str(new_dataset.id))

    # 返回响应
    return serialize_dataset(new_dataset, question_count=question_count, mask_user_id=False)
