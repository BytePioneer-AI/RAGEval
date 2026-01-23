from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.models.user import User
from app.services.model_config_service import get_model_config
from app.services.user_model_config_service import (
    create_user_model_config,
    list_user_model_configs,
    get_user_model_config,
    update_user_model_config,
    delete_user_model_config,
)
from app.schemas.user_model_config import (
    UserModelConfigCreate,
    UserModelConfigUpdate,
    UserModelConfigOut,
)

router = APIRouter()


def _require_tls(request: Request) -> None:
    return


@router.post("", response_model=UserModelConfigOut)
def create_user_model_config_api(
    *,
    db: Session = Depends(get_db),
    user_model_config_in: UserModelConfigCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    绑定用户 API Key 到模型配置
    """
    _require_tls(request)
    model_config = get_model_config(db, model_config_id=user_model_config_in.model_config_id)
    if not model_config:
        raise HTTPException(status_code=404, detail="模型配置未找到")
    if not (model_config.is_public or str(model_config.created_by) == str(current_user.id) or current_user.is_admin):
        raise HTTPException(status_code=403, detail="无权限绑定该模型配置")
    try:
        return create_user_model_config(db, user_id=current_user.id, obj_in=user_model_config_in)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("", response_model=List[UserModelConfigOut])
def read_user_model_configs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    获取当前用户的模型密钥绑定
    """
    return list_user_model_configs(db, user_id=current_user.id)


@router.get("/{user_model_config_id}", response_model=UserModelConfigOut)
def read_user_model_config(
    *,
    db: Session = Depends(get_db),
    user_model_config_id: str,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    获取单个模型密钥绑定
    """
    db_obj = get_user_model_config(db, user_id=current_user.id, config_id=user_model_config_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="模型密钥绑定未找到")
    return db_obj


@router.put("/{user_model_config_id}", response_model=UserModelConfigOut)
def update_user_model_config_api(
    *,
    db: Session = Depends(get_db),
    user_model_config_id: str,
    user_model_config_in: UserModelConfigUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    更新模型密钥绑定
    """
    _require_tls(request)
    db_obj = get_user_model_config(db, user_id=current_user.id, config_id=user_model_config_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="模型密钥绑定未找到")
    try:
        return update_user_model_config(db, db_obj=db_obj, obj_in=user_model_config_in)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/{user_model_config_id}")
def delete_user_model_config_api(
    *,
    db: Session = Depends(get_db),
    user_model_config_id: str,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    删除模型密钥绑定
    """
    db_obj = get_user_model_config(db, user_id=current_user.id, config_id=user_model_config_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="模型密钥绑定未找到")
    delete_user_model_config(db, db_obj=db_obj)
    return {"detail": "模型密钥绑定已删除"}
