from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.question import (
    QuestionCreate, 
    QuestionUpdate, 
    QuestionOut, 
    QuestionBatchCreate
)
from app.services.question_service import (
    create_question,
    get_question,
    get_questions_by_project,
    update_question,
    delete_question,
    create_questions_batch
)
from app.services.project_service import get_project

router = APIRouter()

@router.post("", response_model=QuestionOut)
def create_question_api(
    *,
    db: Session = Depends(get_db),
    question_in: QuestionCreate,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    创建单个问题
    """
    # 检查项目权限
    print("********************")
    print(f"{question_in.project_id}")
    project = get_project(db, project_id=question_in.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目未找到")
    if project.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权限在此项目中添加问题")

    question = create_question(db, obj_in=question_in)
    print("************************============5===")
    return question

@router.post("/batch", response_model=List[QuestionOut])
def create_questions_batch_api(
    *,
    db: Session = Depends(get_db),
    questions_in: QuestionBatchCreate,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    批量创建问题
    """
    # 检查项目权限
    project = get_project(db, project_id=questions_in.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目未找到")
    if project.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权限在此项目中添加问题")
    
    questions = create_questions_batch(db, project_id=questions_in.project_id, questions=questions_in.questions)
    return questions

@router.get("", response_model=List[QuestionOut])
def read_questions(
    db: Session = Depends(get_db),
    project_id: str = Query(..., description="项目ID"),
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = Query(None, description="问题分类过滤"),
    difficulty: Optional[str] = Query(None, description="问题难度过滤"),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    获取项目中的所有问题
    """
    # 检查项目权限
    project = get_project(db, project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目未找到")
    if project.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权限查看此项目")
    
    questions = get_questions_by_project(
        db, project_id=project_id, skip=skip, limit=limit,
        category=category, difficulty=difficulty
    )
    print("************************============")
    print(questions)
    return questions

@router.get("/{question_id}", response_model=QuestionOut)
def read_question(
    *,
    db: Session = Depends(get_db),
    question_id: str,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    获取单个问题详情
    """
    question = get_question(db, question_id=question_id)
    if not question:
        raise HTTPException(status_code=404, detail="问题未找到")
    
    # 检查项目权限
    project = get_project(db, project_id=question.project_id)
    if project.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权限查看此问题")
    
    return question

@router.put("/{question_id}", response_model=QuestionOut)
def update_question_api(
    *,
    db: Session = Depends(get_db),
    question_id: str,
    question_in: QuestionUpdate,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    更新问题
    """
    question = get_question(db, question_id=question_id)
    if not question:
        raise HTTPException(status_code=404, detail="问题未找到")
    
    # 检查项目权限
    project = get_project(db, project_id=question.project_id)
    if project.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权限更新此问题")
    
    question = update_question(db, db_obj=question, obj_in=question_in)
    return question

@router.delete("/{question_id}")
def delete_question_api(
    *,
    db: Session = Depends(get_db),
    question_id: str,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    删除问题
    """
    question = get_question(db, question_id=question_id)
    if not question:
        raise HTTPException(status_code=404, detail="问题未找到")
    
    # 检查项目权限
    project = get_project(db, project_id=question.project_id)
    if project.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权限删除此问题")
    
    delete_question(db, question_id=question_id)
    return {"detail": "问题已删除"}
