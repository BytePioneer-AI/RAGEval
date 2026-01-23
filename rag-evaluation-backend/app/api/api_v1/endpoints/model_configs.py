from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.models.user import User
from app.schemas.model_config import ModelConfigCreate, ModelConfigUpdate, ModelConfigOut
from app.services.model_config_service import (
    create_model_config,
    list_model_configs,
    get_model_config,
    update_model_config,
    delete_model_config,
)

router = APIRouter()


@router.post("", response_model=ModelConfigOut)
def create_model_config_api(
    *,
    db: Session = Depends(get_db),
    model_config_in: ModelConfigCreate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    创建模型配置
    """
    return create_model_config(db, user_id=current_user.id, obj_in=model_config_in)


@router.get("", response_model=List[ModelConfigOut])
def read_model_configs(
    db: Session = Depends(get_db),
    include_public: bool = Query(True, description="是否包含公开模型配置"),
    provider: Optional[str] = Query(None, description="按提供商过滤"),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    获取模型配置列表
    """
    return list_model_configs(
        db,
        user_id=current_user.id,
        include_public=include_public,
        provider=provider,
    )


@router.get("/{model_config_id}", response_model=ModelConfigOut)
def read_model_config(
    *,
    db: Session = Depends(get_db),
    model_config_id: str,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    获取单个模型配置
    """
    db_obj = get_model_config(db, model_config_id=model_config_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="模型配置未找到")
    if not (db_obj.is_public or str(db_obj.created_by) == str(current_user.id) or current_user.is_admin):
        raise HTTPException(status_code=403, detail="无权限访问该模型配置")
    return db_obj


@router.put("/{model_config_id}", response_model=ModelConfigOut)
def update_model_config_api(
    *,
    db: Session = Depends(get_db),
    model_config_id: str,
    model_config_in: ModelConfigUpdate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    更新模型配置
    """
    db_obj = get_model_config(db, model_config_id=model_config_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="模型配置未找到")
    if not (str(db_obj.created_by) == str(current_user.id) or current_user.is_admin):
        raise HTTPException(status_code=403, detail="无权限更新该模型配置")
    return update_model_config(db, db_obj=db_obj, obj_in=model_config_in)


@router.delete("/{model_config_id}")
def delete_model_config_api(
    *,
    db: Session = Depends(get_db),
    model_config_id: str,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    删除模型配置
    """
    db_obj = get_model_config(db, model_config_id=model_config_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="模型配置未找到")
    if not (str(db_obj.created_by) == str(current_user.id) or current_user.is_admin):
        raise HTTPException(status_code=403, detail="无权限删除该模型配置")
    delete_model_config(db, db_obj=db_obj)
    return {"detail": "模型配置已删除"}
