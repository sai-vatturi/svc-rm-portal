from bson import ObjectId

from app.core.pagination import encode_cursor, try_decode_cursor


def test_cursor_roundtrip():
    oid = ObjectId()
    c = encode_cursor(oid)
    out = try_decode_cursor(c)
    assert out == oid
