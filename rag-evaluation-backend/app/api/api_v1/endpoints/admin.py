from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_current_active_admin, get_db
from app.models.user import User
from app.services.admin_service import get_system_statistics as get_system_statistics_service

router = APIRouter()

@router.get("/statistics", response_model=Dict[str, Any])
def get_system_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
) -> Any:
    """
    获取系统统计信息（仅管理员可访问）
    """
    return get_system_statistics_service(db)
