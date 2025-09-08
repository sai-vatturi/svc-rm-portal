from __future__ import annotations

from bson import ObjectId


def to_object_id(value: str) -> ObjectId:
    return ObjectId(value)


def oid_str(oid: ObjectId | None) -> str | None:
    return str(oid) if oid else None
