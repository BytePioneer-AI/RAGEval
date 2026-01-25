from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.model_config import ModelConfig
from app.schemas.model_config import ModelConfigCreate, ModelConfigUpdate
from app.crud import model_config as crud_model_config


def create_model_config(db: Session, user_id: str, obj_in: ModelConfigCreate) -> ModelConfig:
    data = {
        "name": obj_in.name,
        "provider": obj_in.provider,
        "model": obj_in.model,
        "api_base": obj_in.api_base,
        "default_params": obj_in.default_params,
        "is_public": obj_in.is_public,
        "scene": obj_in.scene,
    }
    return crud_model_config.create_model_config(db, user_id=user_id, data=data)


def list_model_configs(
    db: Session,
    user_id: str,
    include_public: bool = True,
    provider: Optional[str] = None,
) -> List[ModelConfig]:
    return crud_model_config.list_model_configs(
        db,
        user_id=user_id,
        include_public=include_public,
        provider=provider,
    )


def get_model_config(db: Session, model_config_id: str) -> Optional[ModelConfig]:
    return crud_model_config.get_model_config(db, model_config_id)


def update_model_config(db: Session, db_obj: ModelConfig, obj_in: ModelConfigUpdate) -> ModelConfig:
    update_data = obj_in.dict(exclude_unset=True)
    return crud_model_config.update_model_config(db, db_obj, update_data)


def delete_model_config(db: Session, db_obj: ModelConfig) -> None:
    crud_model_config.delete_model_config(db, db_obj)
