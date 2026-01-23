from typing import List, Dict, Any, Optional, Union, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
import random
import string
from datetime import datetime, timedelta
import logging

from app.models.accuracy import AccuracyTest, AccuracyTestItem, AccuracyHumanAssignment
from app.models.question import Question
from app.models.rag_answer import RagAnswer
from app.schemas.accuracy import (
    AccuracyTestCreate, 
    AccuracyTestDetail,
    AccuracyTestProgress,
    AccuracyTestItemCreate,
    HumanAssignmentCreate
)
from app.services.accuracy_evaluator import AccuracyEvaluator

logger = logging.getLogger(__name__)

class AccuracyService:
    """精度评测服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_test(self, data: AccuracyTestCreate, user_id: str) -> AccuracyTest:
        """创建新的精度评测"""
        test = AccuracyTest(
            project_id=data.project_id,
            dataset_id=data.dataset_id,
            name=data.name,
            description=data.description,
            evaluation_type=data.evaluation_type,
            scoring_method=data.scoring_method,
            dimensions=data.dimensions,
            weights=data.weights,
            model_config_test=data.model_config_test,
            prompt_template=data.prompt_template,
            version=data.version,
            batch_settings=data.batch_settings,
            created_by=user_id
        )
        
        self.db.add(test)
        self.db.commit()
        self.db.refresh(test)
        
        # 计算问题总数
        question_count = self.db.query(func.count(Question.id)).filter(
            Question.dataset_id == data.dataset_id
        ).scalar()
        
        # 更新问题总数
        test.total_questions = question_count
        self.db.commit()
        
        return test
    
    def get_tests_by_project(self, project_id: str) -> List[AccuracyTest]:
        """获取项目下的所有精度评测"""
        return self.db.query(AccuracyTest).filter(
            AccuracyTest.project_id == project_id
        ).order_by(desc(AccuracyTest.created_at)).all()
    
    def get_test_by_id(self, test_id: str) -> Optional[AccuracyTest]:
        """根据ID获取精度评测"""
        return self.db.query(AccuracyTest).filter(
            AccuracyTest.id == test_id
        ).first()
    
    def get_test_detail(self, test_id: str) -> Optional[AccuracyTestDetail]:
        """获取精度评测详情"""
        test = self.get_test_by_id(test_id)
        if not test:
            return None
            
        # 计算进度
        progress = 0
        if test.total_questions > 0:
            progress = (test.processed_questions / test.total_questions) * 100
        
        # 计算持续时间
        duration_seconds = None
        if test.started_at:
            end_time = test.completed_at or datetime.now()
            duration_seconds = int((end_time - test.started_at).total_seconds())
            
        return AccuracyTestDetail(
            **test.__dict__,
            progress=progress,
            duration_seconds=duration_seconds
        )
    
    def get_test_progress(self, test_id: str) -> AccuracyTestProgress:
        """获取精度评测进度"""
        test = self.get_test_by_id(test_id)
        if not test:
            return AccuracyTestProgress(
                total=0,
                processed=0,
                success=0,
                failed=0,
                progress_percent=0,
                status="unknown"
            )
            
        # 计算进度百分比
        progress_percent = 0
        if test.total_questions > 0:
            progress_percent = (test.processed_questions / test.total_questions) * 100
            
        return AccuracyTestProgress(
            total=test.total_questions,
            processed=test.processed_questions,
            success=test.success_questions,
            failed=test.failed_questions,
            progress_percent=progress_percent,
            status=test.status,
            started_at=test.started_at,
            completed_at=test.completed_at
        )
        
    async def _create_test_items(self, test: AccuracyTest, questions: List[Question]) -> None:
        """创建评测项目"""
        # 先清除已有的评测项
        self.db.query(AccuracyTestItem).filter(
            AccuracyTestItem.evaluation_id == test.id
        ).delete()
        
        # 对每个问题，创建评测项
        for i, question in enumerate(questions):
            # 查找最新的RAG回答
            rag_answer = self.db.query(RagAnswer).filter(
                RagAnswer.question_id == question.id
            ).order_by(desc(RagAnswer.created_at)).first()
            
            if not rag_answer:
                logger.warning(f"问题 {question.id} 没有RAG回答，跳过")
                continue
                
            # 创建评测项
            item = AccuracyTestItem(
                evaluation_id=test.id,
                question_id=question.id,
                rag_answer_id=rag_answer.id,
                sequence_number=i+1,
                status="pending"
            )
            
            self.db.add(item)
            
        self.db.commit()
        
        # 更新总问题数
        test.total_questions = self.db.query(func.count(AccuracyTestItem.id)).filter(
            AccuracyTestItem.evaluation_id == test.id
        ).scalar()
        self.db.commit()
    
    def get_test_items(self, test_id: str, page: int = 1, page_size: int = 10) -> Tuple[List[Dict[str, Any]], int]:
        """获取评测项目列表"""
        query = self.db.query(AccuracyTestItem).join(
            Question, AccuracyTestItem.question_id == Question.id
        ).join(
            RagAnswer, AccuracyTestItem.rag_answer_id == RagAnswer.id
        ).filter(
            AccuracyTestItem.evaluation_id == test_id
        )
        
        # 获取总数
        total = query.count()
        
        # 分页
        items = query.order_by(AccuracyTestItem.sequence_number).offset(
            (page - 1) * page_size
        ).limit(page_size).with_entities(
            AccuracyTestItem,
            Question.question.label("question_content"),
            Question.answer.label("standard_answer"),
            RagAnswer.answer.label("rag_answer_content")
        ).all()
        
        # 处理结果
        result = []
        for item, question_content, standard_answer, rag_answer_content in items:
            item_dict = {
                **item.__dict__,
                "question_content": question_content,
                "standard_answer": standard_answer,
                "rag_answer_content": rag_answer_content
            }
            result.append(item_dict)
            
        return result, total
        
    def create_human_assignment(self, data: HumanAssignmentCreate, user_id: str) -> AccuracyHumanAssignment:
        """创建人工评测分配"""
        # 验证评测存在
        test = self.get_test_by_id(data.evaluation_id)
        if not test:
            raise ValueError(f"评测不存在: {data.evaluation_id}")
            
        # 获取待分配的评测项
        items = self.db.query(AccuracyTestItem).filter(
            AccuracyTestItem.evaluation_id == data.evaluation_id,
            AccuracyTestItem.status.in_(["pending", "ai_completed"])
        ).limit(data.item_count).all()
        
        if not items:
            raise ValueError("没有可分配的评测项")
            
        # 生成随机访问码
        access_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        # 创建分配
        assignment = AccuracyHumanAssignment(
            evaluation_id=data.evaluation_id,
            access_code=access_code,
            evaluator_name=data.evaluator_name,
            evaluator_email=data.evaluator_email,
            item_ids=[str(item.id) for item in items],
            total_items=len(items),
            completed_items=0,
            status="assigned",
            is_active=True,
            created_by=user_id
        )
        
        self.db.add(assignment)
        self.db.commit()
        self.db.refresh(assignment)
        
        return assignment
