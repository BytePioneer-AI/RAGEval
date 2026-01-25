from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session

from app.models.user_model_config import UserModelConfig
from app.models.api_key_audit import ApiKeyAudit


def create_user_model_config(
    db: Session,
    *,
    user_id: str,
    data: Dict[str, Any],
) -> UserModelConfig:
    db_obj = UserModelConfig(user_id=user_id, **data)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def list_user_model_configs(db: Session, user_id: str) -> List[UserModelConfig]:
    return db.query(UserModelConfig).filter(UserModelConfig.user_id == user_id).all()


def get_user_model_config(db: Session, user_id: str, config_id: str) -> Optional[UserModelConfig]:
    return db.query(UserModelConfig).filter(
        UserModelConfig.id == config_id,
        UserModelConfig.user_id == user_id,
    ).first()


def update_user_model_config(
    db: Session,
    db_obj: UserModelConfig,
    update_data: Dict[str, Any],
) -> UserModelConfig:
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_user_model_config(db: Session, db_obj: UserModelConfig) -> None:
    db.delete(db_obj)
    db.commit()


def create_api_key_audit(db: Session, audit_data: Dict[str, Any]) -> ApiKeyAudit:
    audit = ApiKeyAudit(**audit_data)
    db.add(audit)
    db.commit()
    return audit
