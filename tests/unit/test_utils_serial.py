from bson import ObjectId

from app.utils.serial import to_object_id, oid_str


def test_to_object_id_and_oid_str():
    oid = to_object_id(ObjectId().__str__())
    assert isinstance(oid, ObjectId)
    assert oid_str(oid) == str(oid)
    assert oid_str(None) is None
