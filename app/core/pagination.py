from __future__ import annotations

from base64 import urlsafe_b64decode, urlsafe_b64encode
from typing import Generic, Iterable, List, Optional, Sequence, Tuple, TypeVar

from bson import ObjectId
from pydantic import BaseModel, Field

T = TypeVar("T")


class PageQuery(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    cursor: Optional[str] = None


class Paginated(BaseModel, Generic[T]):
    items: List[T]
    next_cursor: Optional[str] = None


def encode_cursor(oid: ObjectId) -> str:
    return urlsafe_b64encode(str(oid).encode()).decode()


def try_decode_cursor(cursor: Optional[str]) -> Optional[ObjectId]:
    if not cursor:
        return None
    try:
        raw = urlsafe_b64decode(cursor.encode()).decode()
        return ObjectId(raw)
    except Exception:
        return None
