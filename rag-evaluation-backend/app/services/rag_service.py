import asyncio
import httpx
import time
import json
import uuid
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy.orm import Session

from app.crud import rag as crud_rag
from app.models.rag_answer import RagAnswer, ApiConfig
from app.models.question import Question
from app.schemas.rag_answer import RagAnswerCreate, ApiRequestConfig


class RagService:
    """RAG answer collection service."""

    def __init__(self, db: Session):
        self.db = db

    async def collect_answer_api(
        self,
        question: Question,
        api_config: ApiRequestConfig,
        source_system: str = "RAG系统",
        collect_performance: bool = True,
    ) -> Tuple[Optional[RagAnswer], Optional[str]]:
        """
        Collect a single answer from a RAG API.
        Returns: (rag_answer, error_message)
        """
        request_data = api_config.request_template.copy()

        def replace_question_placeholder(obj, question_text):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, (dict, list)):
                        obj[key] = replace_question_placeholder(value, question_text)
                    elif isinstance(value, str) and "{{question}}" in value:
                        obj[key] = value.replace("{{question}}", question_text)
                return obj
            if isinstance(obj, list):
                return [replace_question_placeholder(item, question_text) for item in obj]
            return obj

        request_data = replace_question_placeholder(request_data, question.question_text)

        headers = {"Content-Type": "application/json"}
        if api_config.api_key:
            headers["Authorization"] = f"Bearer {api_config.api_key}"

        if api_config.headers:
            headers.update(api_config.headers)

        start_time = time.time()
        first_response_time = None

        try:
            async with httpx.AsyncClient(timeout=api_config.timeout) as client:
                response = await client.post(
                    api_config.endpoint_url,
                    headers=headers,
                    json=request_data,
                )

                first_response_time = int((time.time() - start_time) * 1000)

                if response.status_code != 200:
                    return None, f"API请求失败: {response.status_code} - {response.text}"

                try:
                    response_json = response.json()
                except json.JSONDecodeError:
                    return None, "无法解析API响应JSON"

                answer_text = self._extract_answer_from_response(response_json, api_config.response_path)
                if not answer_text:
                    return None, f"无法从响应中提取回答，路径: {api_config.response_path}"

                total_response_time = int((time.time() - start_time) * 1000)
                character_count = len(answer_text)
                characters_per_second = character_count / (total_response_time / 1000) if total_response_time > 0 else 0

                RagAnswerCreate(
                    question_id=str(question.id),
                    answer_text=answer_text,
                    collection_method="api",
                    source_system=source_system,
                    first_response_time=first_response_time,
                    total_response_time=total_response_time,
                    character_count=character_count,
                    raw_response=response_json,
                    api_config_id=None,
                )

                db_obj = crud_rag.create_rag_answer(
                    self.db,
                    data={
                        "question_id": question.id,
                        "answer_text": answer_text,
                        "collection_method": "api",
                        "source_system": source_system,
                        "first_response_time": first_response_time,
                        "total_response_time": total_response_time,
                        "character_count": character_count,
                        "characters_per_second": characters_per_second,
                        "raw_response": response_json,
                        "answer_metadata": None,
                    },
                )

                return db_obj, None

        except httpx.TimeoutException:
            return None, "API请求超时"
        except Exception as exc:
            return None, f"收集回答时出错: {str(exc)}"

    async def collect_answers_batch(
        self,
        question_ids: List[str],
        api_config: ApiRequestConfig,
        concurrent_requests: int = 1,
        max_attempts: int = 1,
        source_system: str = "RAG系统",
        collect_performance: bool = True,
    ) -> Dict[str, Any]:
        """Collect answers for multiple questions."""
        questions = crud_rag.get_questions_by_ids(self.db, question_ids)
        if not questions:
            return {
                "success": False,
                "error": "未找到任何问题",
                "results": [],
            }

        tasks = []
        for question in questions:
            tasks.append(self.collect_answer_api(question, api_config, source_system, collect_performance))

        semaphore = asyncio.Semaphore(concurrent_requests)

        async def bounded_collect(task):
            async with semaphore:
                return await task

        bounded_tasks = [bounded_collect(task) for task in tasks]
        results = await asyncio.gather(*bounded_tasks)

        success_count = 0
        failed_count = 0
        success_results = []
        error_results = []

        for (answer, error), question in zip(results, questions):
            if answer:
                success_count += 1
                success_results.append({
                    "question_id": str(question.id),
                    "answer_id": str(answer.id),
                    "success": True,
                })
            else:
                failed_count += 1
                error_results.append({
                    "question_id": str(question.id),
                    "success": False,
                    "error": error,
                })

        return {
            "success": True,
            "total": len(questions),
            "success_count": success_count,
            "failed_count": failed_count,
            "results": success_results + error_results,
        }

    def import_answers_manual(
        self,
        answers: List[Dict[str, Any]],
        source_system: str = "手动导入",
    ) -> Dict[str, Any]:
        """Manually import answers."""
        success_count = 0
        failed_count = 0
        results = []

        for answer_data in answers:
            try:
                question_id = answer_data.get("question_id")
                answer_text = answer_data.get("answer_text")

                if not question_id or not answer_text:
                    failed_count += 1
                    results.append({
                        "question_id": question_id,
                        "success": False,
                        "error": "问题ID或回答文本缺失",
                    })
                    continue

                question = crud_rag.get_question(self.db, question_id)
                if not question:
                    failed_count += 1
                    results.append({
                        "question_id": question_id,
                        "success": False,
                        "error": "问题不存在",
                    })
                    continue

                character_count = len(answer_text)
                db_obj = crud_rag.create_rag_answer(
                    self.db,
                    data={
                        "question_id": question.id,
                        "answer_text": answer_text,
                        "collection_method": "manual",
                        "source_system": source_system,
                        "character_count": character_count,
                        "answer_metadata": answer_data.get("metadata"),
                    },
                )

                success_count += 1
                results.append({
                    "question_id": question_id,
                    "answer_id": str(db_obj.id),
                    "success": True,
                })

            except Exception as exc:
                failed_count += 1
                results.append({
                    "question_id": answer_data.get("question_id", "unknown"),
                    "success": False,
                    "error": str(exc),
                })

        return {
            "success": True,
            "total": len(answers),
            "success_count": success_count,
            "failed_count": failed_count,
            "results": results,
        }

    def _extract_answer_from_response(self, response_json: Dict[str, Any], path: str) -> Optional[str]:
        try:
            parts = path.split(".")
            current = response_json

            for part in parts:
                if part in current:
                    current = current[part]
                else:
                    return None

            return current if isinstance(current, str) else str(current)
        except Exception:
            return None

    def get_rag_answer(self, answer_id: str) -> Optional[RagAnswer]:
        return crud_rag.get_rag_answer(self.db, answer_id)

    def get_answers_by_question(
        self,
        question_id: str,
        version: Optional[str] = None,
    ) -> List[RagAnswer]:
        return crud_rag.list_answers_by_question(self.db, question_id, version=version)

    def get_answers_by_project(
        self,
        project_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[RagAnswer]:
        return crud_rag.list_answers_by_project(
            self.db,
            project_id=project_id,
            skip=skip,
            limit=limit,
        )

    def delete_rag_answer(self, answer_id: str) -> bool:
        return crud_rag.delete_rag_answer(self.db, answer_id)

    def get_rag_answer_by_question_and_version(
        self,
        question_id: str,
        version: str,
    ) -> Optional[RagAnswer]:
        return crud_rag.get_rag_answer_by_question_and_version(
            self.db,
            question_id=question_id,
            version=version,
        )

    def create_rag_answer(self, data: Dict[str, Any]) -> RagAnswer:
        return crud_rag.create_rag_answer(self.db, data=data)

    def update_rag_answer(
        self,
        db_obj: RagAnswer,
        update_data: Dict[str, Any],
    ) -> RagAnswer:
        return crud_rag.update_rag_answer(
            self.db,
            db_obj=db_obj,
            update_data=update_data,
        )

    def save_api_config(
        self,
        project_id: str,
        name: str,
        endpoint_url: str,
        auth_type: str = "none",
        auth_config: Optional[Dict[str, Any]] = None,
        request_template: Dict[str, Any] = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> ApiConfig:
        return crud_rag.save_api_config(
            self.db,
            data={
                "project_id": project_id,
                "name": name,
                "endpoint_url": endpoint_url,
                "auth_type": auth_type,
                "auth_config": auth_config or {},
                "request_template": request_template or {},
                "headers": headers or {},
            },
        )

    def get_dataset_versions(self, dataset_id: str) -> List[Dict[str, Any]]:
        version_counts = crud_rag.get_dataset_version_counts(self.db, dataset_id)
        return [{"version": v[0], "count": v[1]} for v in version_counts]
