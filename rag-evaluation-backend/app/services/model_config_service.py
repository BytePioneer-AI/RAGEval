from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.model_config import ModelConfig
from app.schemas.model_config import ModelConfigCreate, ModelConfigUpdate


def create_model_config(db: Session, user_id: str, obj_in: ModelConfigCreate) -> ModelConfig:
    db_obj = ModelConfig(
        name=obj_in.name,
        provider=obj_in.provider,
        model=obj_in.model,
        api_base=obj_in.api_base,
        default_params=obj_in.default_params,
        is_public=obj_in.is_public,
        created_by=user_id,
        scene=obj_in.scene,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def list_model_configs(
    db: Session,
    user_id: str,
    include_public: bool = True,
    provider: Optional[str] = None,
) -> List[ModelConfig]:
    query = db.query(ModelConfig)
    if include_public:
        query = query.filter(or_(ModelConfig.is_public == True, ModelConfig.created_by == user_id))
    else:
        query = query.filter(ModelConfig.created_by == user_id)
    if provider:
        query = query.filter(ModelConfig.provider == provider)
    return query.all()


def get_model_config(db: Session, model_config_id: str) -> Optional[ModelConfig]:
    return db.query(ModelConfig).filter(ModelConfig.id == model_config_id).first()


def update_model_config(db: Session, db_obj: ModelConfig, obj_in: ModelConfigUpdate) -> ModelConfig:
    update_data = obj_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_model_config(db: Session, db_obj: ModelConfig) -> None:
    db.delete(db_obj)
    db.commit()
