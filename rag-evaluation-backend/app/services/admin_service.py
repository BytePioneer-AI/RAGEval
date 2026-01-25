from typing import Any, Dict

from sqlalchemy.orm import Session

from app.crud import admin as crud_admin


def get_system_statistics(db: Session) -> Dict[str, Any]:
    return crud_admin.get_system_statistics(db)
