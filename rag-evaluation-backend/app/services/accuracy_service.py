from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
import uuid
import json
import random
import string
from datetime import datetime, timedelta
import logging
from fastapi import HTTPException

from app.models.accuracy import AccuracyTest, AccuracyTestItem, AccuracyHumanAssignment
from app.models.question import Question
from app.models.rag_answer import RagAnswer
from app.schemas.accuracy import (
    AccuracyTestCreate,
    AccuracyTestDetail,
    AccuracyTestProgress,
    AccuracyTestItemCreate,
    HumanAssignmentCreate,
)
from app.crud import accuracy as crud_accuracy

logger = logging.getLogger(__name__)


class AccuracyService:
    def __init__(self, db: Session):
        self.db = db

    def create_test(self, data: AccuracyTestCreate, user_id: Optional[uuid.UUID] = None) -> AccuracyTest:
        test_data = {
            "project_id": data.project_id,
            "dataset_id": data.dataset_id,
            "name": data.name,
            "description": data.description,
            "evaluation_type": data.evaluation_type,
            "scoring_method": data.scoring_method,
            "dimensions": data.dimensions,
            "weights": data.weights or {dim: 1.0 for dim in data.dimensions},
            "prompt_template": data.prompt_template,
            "version": data.version,
            "model_config_test": data.model_config_test,
            "batch_settings": data.batch_settings or {"batch_size": 10, "timeout_seconds": 300},
            "status": "created",
            "created_by": user_id,
        }
        test = crud_accuracy.create_accuracy_test(self.db, data=test_data)

        questions = crud_accuracy.list_questions_by_dataset(self.db, data.dataset_id)

        test_items = []
        processed_question_ids = set()

        for question in questions:
            if str(question.id) in processed_question_ids:
                continue

            rag_answer = crud_accuracy.get_latest_rag_answer(
                self.db,
                question_id=question.id,
                version=data.version,
            )

            if not rag_answer:
                continue

            test_item = AccuracyTestItem(
                evaluation_id=test.id,
                question_id=question.id,
                rag_answer_id=rag_answer.id,
                sequence_number=len(test_items) + 1,
                status="pending",
            )
            test_items.append(test_item)
            processed_question_ids.add(str(question.id))

        test.total_questions = len(test_items)

        crud_accuracy.bulk_save_accuracy_items(self.db, test_items)
        test = crud_accuracy.save_accuracy_test(self.db, test)

        return test

    def get_tests_by_project(self, project_id: uuid.UUID) -> List[AccuracyTest]:
        return crud_accuracy.list_accuracy_tests_by_project(self.db, project_id)

    def get_test_detail(self, test_id: uuid.UUID) -> Optional[AccuracyTest]:
        return crud_accuracy.get_accuracy_test(self.db, test_id)

    def get_test_items(
        self,
        test_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        score: Optional[float] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        items, total_count = crud_accuracy.get_accuracy_test_items(
            self.db,
            test_id=test_id,
            limit=limit,
            offset=offset,
            status=status,
            score=score,
        )

        result = []
        for item, question_content, reference_answer, rag_answer_content in items:
            item_dict = {
                "id": item.id,
                "evaluation_id": item.evaluation_id,
                "question_id": item.question_id,
                "rag_answer_id": item.rag_answer_id,
                "status": item.status,
                "final_score": item.final_score,
                "final_dimension_scores": item.final_dimension_scores,
                "final_evaluation_reason": item.final_evaluation_reason,
                "final_evaluation_type": item.final_evaluation_type,
                "ai_score": item.ai_score,
                "ai_dimension_scores": item.ai_dimension_scores,
                "ai_evaluation_reason": item.ai_evaluation_reason,
                "ai_evaluation_time": item.ai_evaluation_time,
                "human_score": item.human_score,
                "human_dimension_scores": item.human_dimension_scores,
                "human_evaluation_reason": item.human_evaluation_reason,
                "human_evaluator_id": item.human_evaluator_id,
                "human_evaluation_time": item.human_evaluation_time,
                "sequence_number": item.sequence_number,
                "question_content": question_content,
                "reference_answer": reference_answer,
                "rag_answer_content": rag_answer_content,
            }
            result.append(item_dict)

        return result, total_count

    def start_test(self, test_id: uuid.UUID) -> Optional[AccuracyTest]:
        test = crud_accuracy.get_accuracy_test(self.db, test_id)
        if not test:
            return None

        if test.status not in ["created", "failed"]:
            raise ValueError(f"Test status is {test.status}; cannot start")

        test.status = "running"
        test.started_at = datetime.utcnow()

        return crud_accuracy.save_accuracy_test(self.db, test)

    def update_test_progress(
        self,
        test_id: uuid.UUID,
        processed: int,
        success: int,
        failed: int,
    ) -> Optional[AccuracyTest]:
        test = crud_accuracy.get_accuracy_test(self.db, test_id)
        if not test:
            return None

        test.processed_questions = processed
        test.success_questions = success
        test.failed_questions = failed

        return crud_accuracy.save_accuracy_test(self.db, test)

    def complete_test(self, test_id: uuid.UUID) -> Optional[AccuracyTest]:
        test = crud_accuracy.get_accuracy_test(self.db, test_id)
        if not test:
            return None

        if test.status != "running":
            raise ValueError(f"Test status is {test.status}; cannot complete")

        results_summary = self._calculate_test_results(test_id)

        test.status = "completed"
        test.completed_at = datetime.utcnow()
        test.results_summary = results_summary

        return crud_accuracy.save_accuracy_test(self.db, test)

    def fail_test(self, test_id: uuid.UUID, error_details: Dict[str, Any]) -> Optional[AccuracyTest]:
        test = crud_accuracy.get_accuracy_test(self.db, test_id)
        if not test:
            return None

        test.status = "failed"
        test.results_summary = {
            "error": True,
            "error_message": error_details.get("message", "unknown error"),
            "error_details": error_details,
        }

        return crud_accuracy.save_accuracy_test(self.db, test)

    def submit_test_item_results(self, test_id: uuid.UUID, items: List[Dict[str, Any]]) -> bool:
        test = crud_accuracy.get_accuracy_test(self.db, test_id)
        if not test:
            raise ValueError("Test not found")

        if test.status != "running":
            raise ValueError(f"Test status is {test.status}; cannot submit results")

        for item_data in items:
            question_id = item_data.get("id")
            if not question_id:
                continue

            item = crud_accuracy.get_accuracy_test_item_by_question(
                self.db,
                test_id=test_id,
                question_id=question_id,
            )

            if not item:
                logger.warning(f"Missing test item: {question_id}")
                continue

            if "ai_score" in item_data:
                item.ai_score = item_data.get("ai_score")
                item.ai_dimension_scores = item_data.get("ai_dimension_scores")
                item.ai_evaluation_reason = item_data.get("ai_evaluation_reason")
                item.ai_raw_response = item_data.get("ai_raw_response")
                item.ai_evaluation_time = datetime.utcnow()

                if test.evaluation_type == "ai" or not item.human_score:
                    item.final_score = item.ai_score
                    item.final_dimension_scores = item.ai_dimension_scores
                    item.final_evaluation_reason = item.ai_evaluation_reason
                    item.final_evaluation_type = "ai"
                    logger.info(
                        "Set final AI score item_id=%s score=%s",
                        item.id,
                        item.final_score,
                    )

            if "human_score" in item_data:
                item.human_score = item_data.get("human_score")
                item.human_dimension_scores = item_data.get("human_dimension_scores")
                item.human_evaluation_reason = item_data.get("human_evaluation_reason")
                item.human_evaluator_id = item_data.get("human_evaluator_id")
                item.human_evaluation_time = datetime.utcnow()

                if test.evaluation_type in ["manual", "hybrid"]:
                    item.final_score = item.human_score
                    item.final_dimension_scores = item.human_dimension_scores
                    item.final_evaluation_reason = item.human_evaluation_reason
                    item.final_evaluation_type = "human"
                    logger.info(
                        "Set final human score item_id=%s score=%s",
                        item.id,
                        item.final_score,
                    )

            if "status" in item_data:
                item.status = item_data.get("status")
            else:
                if item.status == "pending":
                    item.status = "ai_completed" if test.evaluation_type == "ai" else "human_completed"
                elif item.status in ["ai_completed", "human_completed"]:
                    item.status = "both_completed"

            crud_accuracy.save_accuracy_test_item(self.db, item)

        self._update_test_status(test_id)

        return True

    def _update_test_status(self, test_id: uuid.UUID) -> None:
        total, processed, failed = crud_accuracy.get_accuracy_test_stats(self.db, test_id)
        test = crud_accuracy.get_accuracy_test(self.db, test_id)

        if test:
            test.processed_questions = processed
            test.failed_questions = failed
            test.success_questions = processed - failed

            if test.status == "running" and test.processed_questions + test.failed_questions >= test.total_questions:
                test.status = "completed"
                test.completed_at = datetime.utcnow()
                test.results_summary = self._calculate_test_results(test_id)

            crud_accuracy.save_accuracy_test(self.db, test)

    def _calculate_test_results(self, test_id: uuid.UUID) -> Dict[str, Any]:
        test = crud_accuracy.get_accuracy_test(self.db, test_id)
        if not test:
            logger.error("Test not found: %s", test_id)
            return {}

        items = crud_accuracy.list_accuracy_items_for_results(self.db, test_id)
        logger.info("Calculating results test_id=%s items=%s", test_id, len(items))

        total_score = 0
        dimension_totals = {}
        dimension_counts = {}

        for item in items:
            if item.final_score is not None:
                try:
                    total_score += float(item.final_score)
                    if item.final_dimension_scores:
                        for dim, score in item.final_dimension_scores.items():
                            if dim not in dimension_totals:
                                dimension_totals[dim] = 0
                                dimension_counts[dim] = 0

                            if score is not None:
                                try:
                                    score_float = float(score)
                                    dimension_totals[dim] += score_float
                                    dimension_counts[dim] += 1
                                except (TypeError, ValueError) as exc:
                                    logger.warning("Invalid dimension score dim=%s score=%s", dim, score)
                                    continue
                except (TypeError, ValueError):
                    logger.warning("Invalid final score item_id=%s score=%s", item.id, item.final_score)
                    continue

        dimension_scores = {}
        for dim in dimension_totals:
            if dimension_counts[dim] > 0:
                try:
                    dimension_scores[dim] = round(dimension_totals[dim] / dimension_counts[dim], 2)
                except Exception:
                    dimension_scores[dim] = 0

        weights = test.weights or {dim: 1.0 for dim in test.dimensions}
        weighted_score = 0
        weight_sum = 0

        for dim, score in dimension_scores.items():
            if dim in weights:
                try:
                    weight = float(weights[dim])
                    weighted_score += score * weight
                    weight_sum += weight
                except (TypeError, ValueError):
                    continue

        overall_score = round(weighted_score / weight_sum, 2) if weight_sum > 0 else 0

        results_summary = {
            "overall_score": overall_score,
            "dimension_scores": dimension_scores,
            "score_distribution": self._calculate_score_distribution(items),
            "evaluation_types": self._calculate_evaluation_types(items),
            "total_evaluated": len(items),
            "evaluation_type": test.evaluation_type,
            "scoring_method": test.scoring_method,
        }

        return results_summary

    def create_human_assignment(
        self,
        data: HumanAssignmentCreate,
        user_id: Optional[uuid.UUID] = None,
    ) -> AccuracyHumanAssignment:
        test = crud_accuracy.get_accuracy_test(self.db, data.evaluation_id)
        if not test:
            raise ValueError("Test not found")

        if test.evaluation_type not in ["manual", "hybrid"]:
            raise ValueError(f"Evaluation type {test.evaluation_type} does not support manual")

        items = crud_accuracy.list_accuracy_items_by_status(
            self.db,
            test_id=data.evaluation_id,
            statuses=["pending", "ai_completed"],
            limit=data.item_count,
        )

        if not items:
            raise ValueError("No items available for assignment")

        access_code = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))

        expiration_date = None
        if data.expiration_days:
            expiration_date = datetime.utcnow() + timedelta(days=data.expiration_days)

        assignment_data = {
            "evaluation_id": data.evaluation_id,
            "access_code": access_code,
            "evaluator_name": data.evaluator_name,
            "evaluator_email": data.evaluator_email,
            "item_ids": [str(item.id) for item in items],
            "total_items": len(items),
            "completed_items": 0,
            "status": "assigned",
            "is_active": True,
            "expiration_date": expiration_date,
            "created_by": user_id,
        }

        return crud_accuracy.create_human_assignment(self.db, data=assignment_data)

    def get_human_assignments(self, test_id: uuid.UUID) -> List[AccuracyHumanAssignment]:
        return crud_accuracy.list_human_assignments(self.db, test_id)

    def check_running_tests(self, project_id: uuid.UUID) -> List[AccuracyTest]:
        return crud_accuracy.list_running_tests(self.db, project_id)

    def mark_test_interrupted(self, test_id: uuid.UUID, reason: str) -> Optional[AccuracyTest]:
        test = crud_accuracy.get_accuracy_test(self.db, test_id)
        if test and test.status == "running":
            test.status = "interrupted"
            test.completed_at = datetime.utcnow()
            return crud_accuracy.save_accuracy_test(self.db, test)
        return test

    def reset_test_items(self, test_id: uuid.UUID) -> bool:
        try:
            crud_accuracy.delete_items_by_status(
                self.db,
                test_id=test_id,
                statuses=["ai_completed", "human_completed", "both_completed"],
            )

            test = crud_accuracy.get_accuracy_test(self.db, test_id)
            if test:
                test.status = "created"
                test.processed_questions = 0
                test.success_questions = 0
                test.failed_questions = 0
                test.results_summary = None
                test.started_at = None
                test.completed_at = None
                crud_accuracy.save_accuracy_test(self.db, test)

            return True
        except Exception as exc:
            crud_accuracy.rollback(self.db)
            logger.error("Failed to reset test items: %s", str(exc))
            return False

    def update_test_status(self, db: Session, test_id: str, status: str) -> Optional[AccuracyTest]:
        test = crud_accuracy.get_accuracy_test(db, test_id)
        if not test:
            raise HTTPException(status_code=404, detail="Test not found")

        test.status = status
        return crud_accuracy.save_accuracy_test(db, test)

    def _calculate_score_distribution(self, items: List[AccuracyTestItem]) -> Dict[str, int]:
        distribution = {"5": 0, "4": 0, "3": 0, "2": 0, "1": 0, "0": 0}

        for item in items:
            if item.final_score is not None:
                score_key = str(int(round(float(item.final_score))))
                if score_key in distribution:
                    distribution[score_key] += 1

        return distribution

    def _calculate_evaluation_types(self, items: List[AccuracyTestItem]) -> Dict[str, int]:
        type_counts = {"ai": 0, "human": 0}

        for item in items:
            if item.final_evaluation_type:
                type_counts[item.final_evaluation_type] += 1

        return type_counts
