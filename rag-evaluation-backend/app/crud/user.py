from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.api_key import ApiKey


def get_user(db: Session, user_id: str) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    return db.query(User).offset(skip).limit(limit).all()


def create_user(db: Session, *, user_data: Dict[str, Any]) -> User:
    db_obj = User(**user_data)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_user(db: Session, db_obj: User, update_data: Dict[str, Any]) -> User:
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_user(db: Session, user_id: str) -> Optional[User]:
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        db.delete(user)
        db.commit()
    return user


def get_api_key(db: Session, api_key_id: str) -> Optional[ApiKey]:
    return db.query(ApiKey).filter(ApiKey.id == api_key_id).first()


def get_user_api_keys(db: Session, user_id: str) -> List[ApiKey]:
    return db.query(ApiKey).filter(ApiKey.user_id == user_id).all()


def create_api_key(db: Session, *, user_id: str, api_key_data: Dict[str, Any]) -> ApiKey:
    db_obj = ApiKey(user_id=user_id, **api_key_data)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_api_key(db: Session, db_obj: ApiKey, update_data: Dict[str, Any]) -> ApiKey:
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_api_key(db: Session, api_key_id: str) -> None:
    db_obj = db.query(ApiKey).filter(ApiKey.id == api_key_id).first()
    if db_obj:
        db.delete(db_obj)
        db.commit()
