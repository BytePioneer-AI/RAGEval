from typing import List, Optional, Dict, Any
from datetime import datetime
import numpy as np
from sqlalchemy.orm import Session

from app.crud import performance as crud_performance
from app.models.performance import PerformanceTest
from app.models.question import Question
from app.models.rag_answer import RagAnswer
from app.schemas.performance import PerformanceTestCreate, PerformanceTestUpdate
from app.services import question_service


class PerformanceService:
    def get(self, db: Session, *, id: str) -> Optional[PerformanceTest]:
        return crud_performance.get_performance_test(db, id)

    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[PerformanceTest]:
        return crud_performance.list_performance_tests(db, skip=skip, limit=limit)

    def get_by_project(self, db: Session, *, project_id: str) -> List[PerformanceTest]:
        return crud_performance.list_performance_tests_by_project(db, project_id)

    def update(self, db: Session, *, db_obj: PerformanceTest, obj_in: PerformanceTestUpdate) -> PerformanceTest:
        update_data = obj_in.dict(exclude_unset=True)
        return crud_performance.update_performance_test(db, db_obj=db_obj, update_data=update_data)

    def create_performance_test(self, db: Session, *, obj_in: PerformanceTestCreate) -> PerformanceTest:
        total_questions = 0
        if obj_in.dataset_id:
            questions = question_service.get_questions_by_dataset(db=db, dataset_id=obj_in.dataset_id)
            total_questions = len(questions)

        data = {
            "name": obj_in.name,
            "project_id": obj_in.project_id,
            "dataset_id": obj_in.dataset_id,
            "description": obj_in.description,
            "concurrency": obj_in.concurrency,
            "version": obj_in.version,
            "config": obj_in.config,
            "rag_config": obj_in.rag_config,
            "total_questions": total_questions,
            "status": "created",
        }
        return crud_performance.create_performance_test(db, data=data)

    def start_performance_test(self, db: Session, *, performance_test_id: str) -> PerformanceTest:
        db_obj = crud_performance.get_performance_test(db, performance_test_id)
        if not db_obj:
            return None

        update_data = {
            "status": "running",
            "started_at": datetime.utcnow(),
        }
        return crud_performance.update_performance_test(db, db_obj=db_obj, update_data=update_data)

    def complete_performance_test(
        self,
        db: Session,
        *,
        performance_test_id: str,
        calculate_metrics: bool = True,
    ) -> PerformanceTest:
        db_obj = crud_performance.get_performance_test(db, performance_test_id)
        if not db_obj:
            return None

        update_data = {
            "status": "completed",
            "completed_at": datetime.utcnow(),
        }

        if calculate_metrics:
            rag_answers = crud_performance.list_rag_answers_by_test(db, performance_test_id)
            metrics = self._calculate_summary_metrics(rag_answers, db_obj)
            success_questions = len([a for a in rag_answers if a.total_response_time is not None])
            failed_questions = len(rag_answers) - success_questions

            update_data.update({
                "summary_metrics": metrics,
                "success_questions": success_questions,
                "failed_questions": failed_questions,
                "processed_questions": len(rag_answers),
            })

        return crud_performance.update_performance_test(db, db_obj=db_obj, update_data=update_data)

    def fail_performance_test(
        self,
        db: Session,
        *,
        performance_test_id: str,
        error_details: Dict[str, Any] = None,
    ) -> PerformanceTest:
        db_obj = crud_performance.get_performance_test(db, performance_test_id)
        if not db_obj:
            return None

        update_data = {
            "status": "failed",
            "completed_at": datetime.utcnow(),
        }
        if error_details:
            update_data["summary_metrics"] = {"error_details": error_details}

        return crud_performance.update_performance_test(db, db_obj=db_obj, update_data=update_data)

    def _calculate_summary_metrics(self, rag_answers: List[RagAnswer], test: PerformanceTest) -> Dict[str, Any]:
        if not rag_answers:
            return {}

        successful_answers = [a for a in rag_answers if a.total_response_time is not None]
        if not successful_answers:
            return {"success_rate": 0, "test_duration_seconds": 0}

        if test.completed_at and test.started_at:
            naive_completed = test.completed_at.replace(tzinfo=None)
            naive_started = test.started_at.replace(tzinfo=None)
            test_duration = (naive_completed - naive_started).total_seconds()
        else:
            test_duration = 0

        first_response_times = [a.first_response_time for a in successful_answers if a.first_response_time is not None]
        total_response_times = [a.total_response_time for a in successful_answers if a.total_response_time is not None]
        character_counts = [a.character_count for a in successful_answers if a.character_count is not None]

        def calculate_percentiles(data):
            if not data:
                return None
            return {
                "avg": float(np.mean(data)),
                "max": float(np.max(data)),
                "min": float(np.min(data)),
                "p50": float(np.percentile(data, 50)),
                "p75": float(np.percentile(data, 75)),
                "p90": float(np.percentile(data, 90)),
                "p95": float(np.percentile(data, 95)),
                "p99": float(np.percentile(data, 99)),
                "samples": len(data),
            }

        return {
            "response_time": {
                "first_token_time": calculate_percentiles(first_response_times),
                "total_time": calculate_percentiles(total_response_times),
            },
            "throughput": {
                "requests_per_second": len(successful_answers) / test_duration if test_duration > 0 else 0,
                "chars_per_second": sum(character_counts) / test_duration if test_duration > 0 else 0,
            },
            "character_stats": {
                "output_chars": calculate_percentiles(character_counts),
            },
            "success_rate": len(successful_answers) / len(rag_answers) if rag_answers else 0,
            "test_duration_seconds": test_duration,
        }

    def get_performance_test_detail(self, db: Session, *, performance_test_id: str) -> Dict[str, Any]:
        test = crud_performance.get_performance_test(db, performance_test_id)
        if not test:
            return None

        rag_answers = crud_performance.list_rag_answers_by_test_ordered(db, performance_test_id)

        return {
            "test": test,
            "rag_answers": rag_answers,
            "total_answers": len(rag_answers),
        }

    def get_qa_pairs(self, db: Session, *, performance_test_id: str, skip: int = 0, limit: int = 50) -> Dict[str, Any]:
        return crud_performance.get_qa_pairs(db, performance_test_id=performance_test_id, skip=skip, limit=limit)

    def check_running_tests(self, project_id: str, db: Session) -> List[PerformanceTest]:
        tests = crud_performance.list_performance_tests_by_project(db, project_id)
        return [test for test in tests if test.status == "running"]

    def mark_test_interrupted(self, db: Session, test_id: str, reason: str = None) -> Optional[PerformanceTest]:
        test = crud_performance.get_performance_test(db, test_id)
        if not test:
            return None

        if test.status == "running":
            update_data = {
                "status": "interrupted",
                "completed_at": datetime.utcnow(),
            }
            return crud_performance.update_performance_test(db, db_obj=test, update_data=update_data)

        return test

    def reset_test(self, db: Session, test_id: str) -> Optional[PerformanceTest]:
        test = crud_performance.get_performance_test(db, test_id)
        if not test:
            return None

        if test.status == "interrupted":
            update_data = {
                "status": "created",
                "processed_questions": 0,
                "success_questions": 0,
                "failed_questions": 0,
                "summary_metrics": {},
                "started_at": None,
                "completed_at": None,
            }
            return crud_performance.update_performance_test(db, db_obj=test, update_data=update_data)

        return test


performance_service = PerformanceService()
