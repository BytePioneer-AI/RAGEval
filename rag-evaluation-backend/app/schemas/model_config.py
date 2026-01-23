from typing import Optional, Dict, Any
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ModelConfigBase(BaseModel):
    name: str
    provider: str
    model: str
    api_base: Optional[str] = None
    default_params: Optional[Dict[str, Any]] = None
    is_public: bool = False
    scene: Optional[str] = None


class ModelConfigCreate(ModelConfigBase):
    pass


class ModelConfigUpdate(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    api_base: Optional[str] = None
    default_params: Optional[Dict[str, Any]] = None
    is_public: Optional[bool] = None
    scene: Optional[str] = None


class ModelConfigOut(ModelConfigBase):
    id: str
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
