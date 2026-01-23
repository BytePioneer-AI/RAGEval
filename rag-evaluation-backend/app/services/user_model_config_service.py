from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.user_model_config import UserModelConfig
from app.models.api_key_audit import ApiKeyAudit
from app.schemas.user_model_config import UserModelConfigCreate, UserModelConfigUpdate
from app.utils.crypto import encrypt_api_key, decrypt_api_key, hash_api_key, get_key_last4


def create_user_model_config(
    db: Session,
    user_id: str,
    obj_in: UserModelConfigCreate,
) -> UserModelConfig:
    encrypted = encrypt_api_key(obj_in.api_key)
    last4 = get_key_last4(obj_in.api_key)
    key_hash = hash_api_key(obj_in.api_key)
    db_obj = UserModelConfig(
        user_id=user_id,
        model_config_id=obj_in.model_config_id,
        alias=obj_in.alias,
        key_encrypted=encrypted,
        key_last4=last4,
        key_hash=key_hash,
        is_active=obj_in.is_active,
    )
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
    obj_in: UserModelConfigUpdate,
) -> UserModelConfig:
    update_data = obj_in.dict(exclude_unset=True)
    if "api_key" in update_data:
        api_key = update_data.pop("api_key")
        db_obj.key_encrypted = encrypt_api_key(api_key)
        db_obj.key_last4 = get_key_last4(api_key)
        db_obj.key_hash = hash_api_key(api_key)
        db_obj.rotated_at = datetime.utcnow()

    if "is_active" in update_data and update_data["is_active"] is False:
        db_obj.revoked_at = datetime.utcnow()

    for field, value in update_data.items():
        setattr(db_obj, field, value)

    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_user_model_config(db: Session, db_obj: UserModelConfig) -> None:
    db.delete(db_obj)
    db.commit()


def decrypt_user_api_key(
    db: Session,
    db_obj: UserModelConfig,
) -> Tuple[str, UserModelConfig]:
    plaintext = decrypt_api_key(db_obj.key_encrypted)
    audit = ApiKeyAudit(
        user_id=db_obj.user_id,
        model_config_id=db_obj.model_config_id,
        user_model_config_id=db_obj.id,
        key_last4=db_obj.key_last4,
    )
    db.add(audit)
    db.commit()
    return plaintext, db_obj
