from typing import Any, List, Optional, Dict
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Body, BackgroundTasks
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.rag_answer import (
    RagAnswerOut, 
    RagAnswerDetail,
    BatchCollectionRequest,
    BatchImportRequest,
    ApiRequestConfig,
    CollectionProgress,
    RagAnswerCreate,
    RagAnswerUpdate
)
from app.services.rag_service import RagService
from app.services.project_service import get_project as service_get_project
from app.services.question_service import (
    get_question as service_get_question,
    get_questions_by_ids_for_project as service_get_questions_by_ids_for_project,
)
from app.services.dataset_service import get_dataset as service_get_dataset

router = APIRouter()

@router.post("/collect", response_model=Dict[str, Any])
async def collect_rag_answers(
    *,
    db: Session = Depends(get_db),
    req: BatchCollectionRequest,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    从RAG系统API收集回答
    """
    # 检查项目权限
    project = service_get_project(db, req.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目未找到")
    if project.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权在此项目中收集回答")
    
    # 检查问题是否属于项目
    questions = service_get_questions_by_ids_for_project(
        db,
        question_ids=req.question_ids,
        project_id=req.project_id,
    )
    
    if len(questions) != len(req.question_ids):
        raise HTTPException(status_code=400, detail="部分问题ID无效或不属于此项目")
    
    # 创建服务实例并收集回答
    rag_service = RagService(db)
    results = await rag_service.collect_answers_batch(
        req.question_ids,
        req.api_config,
        req.concurrent_requests,
        req.max_attempts,
        req.source_system,
        req.collect_performance
    )
    
    return results

@router.post("/import", response_model=Dict[str, Any])
def import_rag_answers(
    *,
    db: Session = Depends(get_db),
    req: BatchImportRequest,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    手动导入RAG回答
    """
    # 检查项目权限
    project = service_get_project(db, req.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目未找到")
    if project.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权在此项目中导入回答")
    
    # 导入回答
    rag_service = RagService(db)
    results = rag_service.import_answers_manual(
        req.answers,
        req.source_system
    )
    
    return results

@router.get("/project/{project_id}", response_model=List[RagAnswerOut])
def read_project_answers(
    *,
    db: Session = Depends(get_db),
    project_id: str,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    获取项目的所有RAG回答
    """
    # 检查项目权限
    project = service_get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目未找到")
    if project.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权查看此项目的回答")
    
    # 获取回答
    rag_service = RagService(db)
    answers = rag_service.get_answers_by_project(project_id, skip, limit)
    
    return answers

@router.get("/question/{question_id}", response_model=List[RagAnswerOut])
def read_question_answers(
    *,
    db: Session = Depends(get_db),
    question_id: str,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    获取问题的所有RAG回答
    """
    # 检查问题是否存在
    question = service_get_question(db, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="问题未找到")
    
    dataset = service_get_dataset(db, str(question.dataset_id))
    if not dataset:
        raise HTTPException(status_code=404, detail="相关数据集未找到")

    if str(dataset.user_id) != str(current_user.id) and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权查看此问题的回答")
    
    # 获取回答
    rag_service = RagService(db)
    answers = rag_service.get_answers_by_question(question_id)
    
    return answers

@router.get("/{answer_id}", response_model=RagAnswerDetail)
def read_rag_answer(
    *,
    db: Session = Depends(get_db),
    answer_id: str,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    获取单个RAG回答详情
    """
    # 获取回答
    rag_service = RagService(db)
    answer = rag_service.get_rag_answer(answer_id)
    
    if not answer:
        raise HTTPException(status_code=404, detail="回答未找到")
    
    # 检查权限
    question = service_get_question(db, answer.question_id)
    if not question:
        raise HTTPException(status_code=404, detail="相关问题未找到")

    dataset = service_get_dataset(db, str(question.dataset_id))
    if not dataset:
        raise HTTPException(status_code=404, detail="相关数据集未找到")

    if str(dataset.user_id) != str(current_user.id) and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权查看此回答")
    
    return answer

@router.delete("/{answer_id}", response_model=Dict[str, Any])
def delete_rag_answer(
    *,
    db: Session = Depends(get_db),
    answer_id: str,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    删除RAG回答
    """
    rag_service = RagService(db)
    answer = rag_service.get_rag_answer(answer_id)
    
    if not answer:
        raise HTTPException(status_code=404, detail="回答未找到")
    
    # 检查权限 - 修复从问题查询到数据集
    question = service_get_question(db, answer.question_id)
    if not question:
        raise HTTPException(status_code=404, detail="相关问题未找到")

    dataset = service_get_dataset(db, str(question.dataset_id))
    if not dataset:
        raise HTTPException(status_code=404, detail="相关数据集未找到")

    if str(dataset.user_id) != str(current_user.id) and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权删除此回答")
    
    # 删除回答
    rag_service.delete_rag_answer(answer_id)
    
    return {"detail": "回答已删除"}

@router.post("", response_model=RagAnswerOut)
def create_rag_answer(
    *,
    db: Session = Depends(get_db),
    rag_answer_in: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    创建RAG回答
    """
    # 基本验证
    required_fields = ["question_id", "answer", "version"]
    for field in required_fields:
        if field not in rag_answer_in:
            raise HTTPException(status_code=400, detail=f"缺少必要字段: {field}")
    
    # 检查问题是否存在
    question = service_get_question(db, rag_answer_in["question_id"])
    if not question:
        raise HTTPException(status_code=404, detail="问题未找到")
    
    # 检查是否已经存在相同版本的回答
    rag_service = RagService(db)
    existing_answer = rag_service.get_rag_answer_by_question_and_version(
        rag_answer_in["question_id"],
        rag_answer_in["version"],
    )
    
    if existing_answer:
        raise HTTPException(status_code=400, detail=f"该问题的 {rag_answer_in['version']} 版本回答已存在")

    # 只提取数据库模型支持的字段
    valid_fields = ["question_id", "answer", "collection_method", "version", 
                    "first_response_time", "total_response_time", "character_count", "raw_response"
                    ,'charactersPerSecond'
                    ,'sequenceNumber' 
                    ,'characters_per_second'
                    ,'performance_test_id']
    
    rag_answer_data = {k: v for k, v in rag_answer_in.items() if k in valid_fields}
    
    # 设置默认值
    if "collection_method" not in rag_answer_data:
        rag_answer_data["collection_method"] = "manual"
    
    # 创建RAG回答
    rag_answer = rag_service.create_rag_answer(rag_answer_data)
    
    return rag_answer

@router.get("/question/{question_id}/version/{version}", response_model=RagAnswerOut)
def get_rag_answer_by_version(
    *,
    db: Session = Depends(get_db),
    question_id: str,
    version: str,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    获取指定问题的特定版本RAG回答
    """
    rag_service = RagService(db)
    rag_answer = rag_service.get_rag_answer_by_question_and_version(question_id, version)
    
    if not rag_answer:
        raise HTTPException(status_code=404, detail="未找到指定版本的RAG回答")
    
    return rag_answer

@router.get("/question/{question_id}/versions", response_model=List[RagAnswerOut])
def get_all_rag_answer_versions(
    *,
    db: Session = Depends(get_db),
    question_id: str,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    获取问题的所有版本RAG回答
    """
    rag_service = RagService(db)
    rag_answers = rag_service.get_answers_by_question(question_id)
    
    return rag_answers

@router.put("/{answer_id}", response_model=RagAnswerOut)
def update_rag_answer(
    *,
    db: Session = Depends(get_db),
    answer_id: str,
    rag_answer_in: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    更新RAG回答
    """
    rag_service = RagService(db)
    rag_answer = rag_service.get_rag_answer(answer_id)
    if not rag_answer:
        raise HTTPException(status_code=404, detail="回答未找到")
    
    # 检查权限 - 修复从问题查询到数据集
    question = service_get_question(db, rag_answer.question_id)
    if not question:
        raise HTTPException(status_code=404, detail="相关问题未找到")
    
    dataset = service_get_dataset(db, str(question.dataset_id))
    if not dataset:
        raise HTTPException(status_code=404, detail="相关数据集未找到")
    
    # 检查用户权限 (使用数据集的user_id)
    if str(dataset.user_id) != str(current_user.id) and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权更新此回答")
    
    # 如果版本发生变化，检查是否会与现有版本冲突
    if "version" in rag_answer_in and rag_answer_in["version"] != rag_answer.version:
        existing_version = rag_service.get_rag_answer_by_question_and_version(
            rag_answer.question_id,
            rag_answer_in["version"],
        )
        
        if existing_version and str(existing_version.id) != str(answer_id):
            raise HTTPException(status_code=400, detail=f"该问题的 {rag_answer_in['version']} 版本回答已存在")
    
    # 只更新模型支持的字段
    valid_fields = ["answer", "collection_method", "version", 
                   "first_response_time", "total_response_time", "character_count", "raw_response"]
    
    update_data = {k: v for k, v in rag_answer_in.items() if k in valid_fields}
    return rag_service.update_rag_answer(rag_answer, update_data)

@router.get("/versions/dataset/{dataset_id}", response_model=List[Dict[str, Any]])
def get_dataset_rag_versions(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取数据集下的所有RAG回答版本"""
    service = RagService(db)
    versions = service.get_dataset_versions(dataset_id)
    return versions 
