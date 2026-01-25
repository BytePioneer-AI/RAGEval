from typing import List, Optional, Dict, Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.model_config import ModelConfig


def create_model_config(db: Session, *, user_id: str, data: Dict[str, Any]) -> ModelConfig:
    db_obj = ModelConfig(created_by=user_id, **data)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def list_model_configs(
    db: Session,
    *,
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


def update_model_config(db: Session, db_obj: ModelConfig, update_data: Dict[str, Any]) -> ModelConfig:
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_model_config(db: Session, db_obj: ModelConfig) -> None:
    db.delete(db_obj)
    db.commit()
