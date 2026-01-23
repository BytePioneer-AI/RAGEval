from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


class UserModelConfigBase(BaseModel):
    model_config_id: str
    alias: Optional[str] = None
    is_active: bool = True


class UserModelConfigCreate(UserModelConfigBase):
    api_key: str = Field(..., min_length=5)


class UserModelConfigUpdate(BaseModel):
    alias: Optional[str] = None
    api_key: Optional[str] = Field(None, min_length=5)
    is_active: Optional[bool] = None


class UserModelConfigOut(UserModelConfigBase):
    id: str
    user_id: str
    key_last4: str
    key_hash: Optional[str] = None
    rotated_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
