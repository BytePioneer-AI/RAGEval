from typing import Any, List, Optional
import io
import pandas as pd
from fastapi.responses import StreamingResponse
import urllib.parse

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.question import (
    QuestionCreate,
    QuestionUpdate,
    QuestionOut,
    BatchDeleteRequest,
    QuestionBase,
)
from app.schemas.common import PaginatedResponse
from app.services.dataset_service import get_dataset as service_get_dataset
from app.services.question_service import (
    get_question as service_get_question,
    create_question as service_create_question,
    update_question as service_update_question,
    delete_question as service_delete_question,
    create_questions_batch as service_create_questions_batch,
    create_question_with_rag_answer as service_create_question_with_rag_answer,
    create_questions_with_rag_answers as service_create_questions_with_rag_answers,
    delete_questions_by_ids as service_delete_questions_by_ids,
    list_dataset_questions_with_rag_answers,
    list_questions_for_export,
)

router = APIRouter()

@router.get("/{dataset_id}/questions", response_model=PaginatedResponse[QuestionOut])
def read_questions(
    *,
    db: Session = Depends(get_db),
    dataset_id: str,
    page: int = Query(1, gt=0),
    size: int = Query(10, gt=0, le=100),
    search: Optional[str] = None,
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    version: Optional[str] = None,  # 用于筛选特定版本的RAG答案
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    获取数据集的问题列表，如果指定version，只返回有该版本RAG答案的问题
    """
    dataset = service_get_dataset(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集未找到")

    if not dataset.is_public and str(dataset.user_id) != str(current_user.id) and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权访问此数据集")

    skip = (page - 1) * size
    result = list_dataset_questions_with_rag_answers(
        db,
        dataset_id=dataset_id,
        skip=skip,
        limit=size,
        search=search,
        category=category,
        difficulty=difficulty,
        version=version,
    )

    total = result["total"]
    return {
        "items": result["items"],
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size if total > 0 else 1,
    }

@router.post("/{dataset_id}/questions", response_model=QuestionOut)
def create_question(
    *,
    db: Session = Depends(get_db),
    dataset_id: str,
    question_in: dict = Body(...),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    创建问题
    """
    dataset = service_get_dataset(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集未找到")

    if str(dataset.user_id) != str(current_user.id) and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权操作此数据集")

    tags = question_in.get("tags", {})
    if isinstance(tags, list):
        tags = {tag: True for tag in tags}

    question_in_data = QuestionCreate(
        dataset_id=dataset_id,
        question_text=question_in["question_text"],
        standard_answer=question_in["standard_answer"],
        category=question_in.get("category"),
        difficulty=question_in.get("difficulty"),
        type=question_in.get("type", "text"),
        tags=tags,
        question_metadata=question_in.get("question_metadata", {}),
    )
    question = service_create_question(db, question_in_data)

    return {
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
        "updated_at": question.updated_at,
    }

@router.put("/{dataset_id}/questions/{question_id}", response_model=QuestionOut)
def update_question(
    *,
    db: Session = Depends(get_db),
    dataset_id: str,
    question_id: str,
    question_in: QuestionUpdate = Body(...),  # 同样修改为使用dict
    current_user: User = Depends(get_current_user)
) -> Any:
    print("==============")

    print(question_in.dict(exclude_unset=True))

    """
    更新问题
    """
    dataset = service_get_dataset(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集未找到")

    if str(dataset.user_id) != str(current_user.id) and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权操作此数据集")

    question = service_get_question(db, question_id)
    if not question or str(question.dataset_id) != str(dataset_id):
        raise HTTPException(status_code=404, detail="问题未找到")

    question = service_update_question(db, question, question_in)
    
    return {
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

@router.delete("/{dataset_id}/questions/{question_id}", response_model=dict)
def delete_question(
    *,
    db: Session = Depends(get_db),
    dataset_id: str,
    question_id: str,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    删除问题
    """
    dataset = service_get_dataset(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集未找到")

    if str(dataset.user_id) != str(current_user.id) and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权操作此数据集")

    question = service_get_question(db, question_id)
    if not question or str(question.dataset_id) != str(dataset_id):
        raise HTTPException(status_code=404, detail="问题未找到")

    service_delete_question(db, question_id)
    
    return {"detail": "问题已删除"}

@router.post("/{dataset_id}/questions/batch-delete", response_model=dict)
def batch_delete_questions(
    *,
    db: Session = Depends(get_db),
    dataset_id: str,
    delete_data: BatchDeleteRequest,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    批量删除问题
    """
    dataset = service_get_dataset(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集未找到")

    if str(dataset.user_id) != str(current_user.id) and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权操作此数据集")

    deleted_count = service_delete_questions_by_ids(
        db,
        dataset_id=dataset_id,
        question_ids=delete_data.question_ids,
    )
    if deleted_count == 0:
        raise HTTPException(status_code=404, detail="未找到要删除的问题")

    return {"detail": f"已删除 {deleted_count} 个问题"}

@router.post("/{dataset_id}/questions/with-rag", response_model=QuestionOut)
def create_question_with_rag(
    *,
    db: Session = Depends(get_db),
    dataset_id: str,
    question_data: dict = Body(...),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    创建问题并同时创建RAG回答
    """
    dataset = service_get_dataset(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集未找到")

    if str(dataset.user_id) != str(current_user.id) and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权操作此数据集")

    rag_answer_data = question_data.pop("rag_answer", None)

    tags = question_data.get("tags", {})
    if isinstance(tags, list):
        tags = {tag: True for tag in tags}

    question_payload = {
        "dataset_id": dataset_id,
        "question_text": question_data["question_text"],
        "standard_answer": question_data["standard_answer"],
        "category": question_data.get("category"),
        "difficulty": question_data.get("difficulty"),
        "type": question_data.get("type", "text"),
        "tags": tags,
        "question_metadata": question_data.get("question_metadata", {}),
    }

    rag_payload = None
    if rag_answer_data:
        answer_text = rag_answer_data.pop("answer_text", None)
        rag_payload = {
            "answer": answer_text,
            "collection_method": rag_answer_data.get("collection_method", "manual"),
            "version": rag_answer_data.get("version", "v1"),
        }

    return service_create_question_with_rag_answer(
        db,
        question_data=question_payload,
        rag_answer_data=rag_payload,
    )

# 批量创建问题
@router.post("/{dataset_id}/questions/batch", response_model=dict)
def batch_create_questions(
    *,
    db: Session = Depends(get_db),
    dataset_id: str,
    data: dict = Body(...),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    批量创建问题
    """
    dataset = service_get_dataset(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集未找到")

    if str(dataset.user_id) != str(current_user.id) and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权操作此数据集")

    questions_data = data.get("questions", [])

    MAX_BATCH_SIZE = 500  # 设置批量上限
    if len(questions_data) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"批量添加数量超过限制（最大{MAX_BATCH_SIZE}条）",
        )

    prepared_questions = []
    for q_data in questions_data:
        try:
            tags = q_data.get("tags", {})
            if isinstance(tags, list):
                tags = {tag: True for tag in tags}

            question_payload = QuestionBase(
                question_text=q_data["question_text"],
                standard_answer=q_data["standard_answer"],
                category=q_data.get("category"),
                difficulty=q_data.get("difficulty"),
                type=q_data.get("type", "text"),
                tags=tags,
                question_metadata=q_data.get("question_metadata", {}),
            )
            prepared_questions.append(question_payload)
        except Exception as exc:
            print(f"Error creating question: {str(exc)}")

    created_questions = service_create_questions_batch(
        db,
        dataset_id=dataset_id,
        questions=prepared_questions,
    )

    return {
        "success": True,
        "imported_count": len(created_questions),
        "total_count": len(questions_data),
    }

# 批量创建带RAG回答的问题
@router.post("/{dataset_id}/questions/batch-with-rag", response_model=dict)
def batch_create_questions_with_rag(
    *,
    db: Session = Depends(get_db),
    dataset_id: str,
    data: dict = Body(...),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    批量创建带RAG回答的问题
    """
    dataset = service_get_dataset(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集未找到")

    if str(dataset.user_id) != str(current_user.id) and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权操作此数据集")

    questions_data = data.get("questions", [])

    MAX_BATCH_SIZE = 200  # 带RAG回答的批量限制可以小一些
    if len(questions_data) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"批量添加数量超过限制（最大{MAX_BATCH_SIZE}条）",
        )

    prepared_questions = []
    for q_data in questions_data:
        try:
            rag_answer_data = q_data.get("rag_answer")

            tags = q_data.get("tags", {})
            if isinstance(tags, list):
                tags = {tag: True for tag in tags}

            question_payload = {
                "question_text": q_data["question_text"],
                "standard_answer": q_data["standard_answer"],
                "category": q_data.get("category"),
                "difficulty": q_data.get("difficulty"),
                "type": q_data.get("type", "text"),
                "tags": tags,
                "question_metadata": q_data.get("question_metadata", {}),
            }

            if rag_answer_data:
                answer_text = rag_answer_data.get("answer_text")
                rag_payload = {
                    "answer": answer_text,
                    "collection_method": rag_answer_data.get("collection_method", "import"),
                    "version": rag_answer_data.get("version", "v1"),
                }
                question_payload["rag_answer"] = rag_payload

            prepared_questions.append(question_payload)
        except Exception as exc:
            print(f"Error creating question with RAG: {str(exc)}")

    try:
        created_questions = service_create_questions_with_rag_answers(
            db,
            dataset_id=dataset_id,
            questions_data=prepared_questions,
        )
        return {
            "success": True,
            "imported_count": len(created_questions),
            "total_count": len(questions_data),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"批量创建失败: {str(exc)}")

@router.get("/{dataset_id}/export")
def export_questions(
    *,
    db: Session = Depends(get_db),
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    search: Optional[str] = None,
    category: Optional[str] = None,
    difficulty: Optional[str] = None
) -> Any:
    """
    导出数据集问题为Excel
    """
    dataset = service_get_dataset(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集未找到")

    if not dataset.is_public and str(dataset.user_id) != str(current_user.id) and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权访问此数据集")

    questions = list_questions_for_export(
        db,
        dataset_id=dataset_id,
        search=search,
        category=category,
        difficulty=difficulty,
    )
    
    # 准备数据
    data = []
    for q in questions:
        # 处理标签，确保兼容不同的数据格式
        tags_str = ""
        if q.tags:
            if isinstance(q.tags, dict):
                # 如果是字典格式，使用键作为标签
                tags_str = ", ".join(q.tags.keys())
            elif isinstance(q.tags, list):
                # 如果是列表格式，直接连接元素
                tags_str = ", ".join(q.tags)
            else:
                # 其他情况，转换为字符串
                tags_str = str(q.tags)
        
        data.append({
            "问题": q.question_text,
            "标准答案": q.standard_answer,
            "分类": q.category,
            "难度": q.difficulty,
            # "类型": q.type,
            "标签": tags_str,
        })
    
    # 创建DataFrame
    df = pd.DataFrame(data)
    
    # 生成Excel文件
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='问题列表', index=False)
        
        # 获取工作簿和工作表对象
        workbook = writer.book
        worksheet = writer.sheets['问题列表']
        
        # 设置列宽
        worksheet.set_column('A:A', 40)  # 问题
        worksheet.set_column('B:B', 40)  # 标准答案
        worksheet.set_column('C:C', 15)  # 分类
        worksheet.set_column('D:D', 10)  # 难度
        worksheet.set_column('E:E', 10)  # 类型
        worksheet.set_column('F:F', 20)  # 标签
    
    # 重置文件指针位置
    output.seek(0)
    
    # 使用ASCII字符构建安全的文件名
    safe_name = dataset.name.replace(" ", "_").replace("/", "_").replace("\\", "_")
    filename = f"dataset_{dataset_id}_questions.xlsx"
    
    # 使用RFC 5987规范处理文件名的Content-Disposition
    encoded_filename = urllib.parse.quote(filename)
    content_disposition = f"attachment; filename=\"{encoded_filename}\"; filename*=UTF-8''{encoded_filename}"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": content_disposition}
    ) 
