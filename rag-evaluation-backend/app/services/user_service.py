from typing import Optional, List

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.user import User
from app.models.api_key import ApiKey
from app.schemas.user import UserCreate, UserUpdate
from app.schemas.api_key import ApiKeyCreate, ApiKeyUpdate
from app.crud import user as crud_user

def get_user(db: Session, user_id: str) -> Optional[User]:
    return crud_user.get_user(db, user_id)

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return crud_user.get_user_by_email(db, email)

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    return crud_user.get_users(db, skip=skip, limit=limit)

def get_api_key(db: Session, api_key_id: str) -> Optional[ApiKey]:
    return crud_user.get_api_key(db, api_key_id)

def get_user_api_keys(db: Session, user_id: str) -> List[ApiKey]:
    return crud_user.get_user_api_keys(db, user_id)

def create_user(db: Session, obj_in: UserCreate) -> User:
    user_data = {
        "email": obj_in.email,
        "password_hash": get_password_hash(obj_in.password),
        "name": obj_in.name,
        "company": obj_in.company,
        "bio": obj_in.bio,
        "avatar_url": obj_in.avatar_url,
        "is_active": obj_in.is_active,
        "is_admin": obj_in.is_admin,
    }
    return crud_user.create_user(db, user_data=user_data)

def update_user(db: Session, db_obj: User, obj_in: UserUpdate) -> User:
    update_data = obj_in.dict(exclude_unset=True)
    if update_data.get("password"):
        hashed_password = get_password_hash(update_data["password"])
        update_data["password_hash"] = hashed_password
        del update_data["password"]

    return crud_user.update_user(db, db_obj, update_data)

def delete_user(db: Session, user_id: str) -> Optional[User]:
    return crud_user.delete_user(db, user_id)

def create_api_key(db: Session, user_id: str, obj_in: ApiKeyCreate) -> ApiKey:
    api_key_data = {
        "name": obj_in.name,
        "key": obj_in.key,
        "provider": obj_in.provider,
        "is_active": obj_in.is_active,
    }
    return crud_user.create_api_key(db, user_id=user_id, api_key_data=api_key_data)

def update_api_key(db: Session, db_obj: ApiKey, obj_in: ApiKeyUpdate) -> ApiKey:
    update_data = obj_in.dict(exclude_unset=True)
    return crud_user.update_api_key(db, db_obj, update_data)

def delete_api_key(db: Session, api_key_id: str) -> None:
    crud_user.delete_api_key(db, api_key_id)
