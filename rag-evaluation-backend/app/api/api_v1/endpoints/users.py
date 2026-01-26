from typing import Any, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import EmailStr

from app.api.deps import get_current_active_admin, get_db, get_current_active_user
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserOut
from app.services.user_service import (
    get_user as service_get_user,
    get_user_by_email as service_get_user_by_email,
    get_users as service_get_users,
    create_user as service_create_user,
    update_user as service_update_user,
    delete_user as service_delete_user,
)

router = APIRouter()


@router.get("", response_model=List[UserOut])
def read_users(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_admin),
) -> Any:
    """
    获取所有用户
    """
    users = service_get_users(db, skip=skip, limit=limit)
    return users


@router.post("", response_model=UserOut)
def create_user_admin(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate,
    current_user: User = Depends(get_current_active_admin),
) -> Any:
    """
    创建新用户 (仅管理员)
    """
    user = service_get_user_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="该邮箱已被注册",
        )
    user = service_create_user(db, obj_in=user_in)
    return user


@router.get("/me", response_model=UserOut)
def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    获取当前登录用户的信息
    """
    user_dict = current_user.__dict__.copy()
    user_dict["id"] = str(user_dict["id"])
    return user_dict


@router.put("/me", response_model=UserOut)
def update_current_user_info(
    *,
    db: Session = Depends(get_db),
    password: Optional[str] = Body(None),
    name: Optional[str] = Body(None),
    email: Optional[EmailStr] = Body(None),
    company: Optional[str] = Body(None),
    bio: Optional[str] = Body(None),
    avatar_url: Optional[str] = Body(None),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    更新当前登录用户的信息
    """
    current_user_data = UserUpdate()
    
    if password is not None:
        current_user_data.password = password
    if name is not None:
        current_user_data.name = name
    if email is not None:
        current_user_data.email = email
    if company is not None:
        current_user_data.company = company
    if bio is not None:
        current_user_data.bio = bio
    if avatar_url is not None:
        current_user_data.avatar_url = avatar_url
    
    return service_update_user(db, current_user, current_user_data)


@router.get("/{user_id}", response_model=UserOut)
def get_user_by_id(
    *,
    db: Session = Depends(get_db),
    user_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    通过ID获取用户信息
    普通用户只能获取自己的信息，管理员可以获取任何用户的信息
    """
    if str(current_user.id) != user_id and not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="无权限查看此用户信息"
        )
    
    user = service_get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="用户未找到"
        )
    
    return user


@router.put("/{user_id}", response_model=UserOut)
def update_user_by_id(
    *,
    db: Session = Depends(get_db),
    user_id: str,
    user_in: UserUpdate,
    current_user: User = Depends(get_current_active_admin)
) -> Any:
    """
    更新指定用户信息
    仅管理员可操作
    """
    user = service_get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="用户未找到"
        )
    
    return service_update_user(db, user, user_in)


@router.delete("/{user_id}", response_model=UserOut)
def delete_user(
    *,
    db: Session = Depends(get_db),
    user_id: str,
    current_user: User = Depends(get_current_active_admin)
) -> Any:
    """
    删除指定用户
    仅管理员可操作
    """
    user = service_get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="用户未找到"
        )
    
    if str(user.id) == str(current_user.id):
        raise HTTPException(
            status_code=400,
            detail="不能删除当前登录的管理员账户"
        )
    
    user_out = UserOut.model_validate(user)
    service_delete_user(db, user_id)
    
    return user_out
