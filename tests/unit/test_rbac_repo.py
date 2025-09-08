from datetime import datetime
from bson import ObjectId
import pytest

from app.repositories.rbac_repo import RbacRepository
from app.models.rbac import User, Role


class _Cursor:
    def __init__(self, docs):
        self._docs = list(docs)
        self._sort = None
    def sort(self, field, direction=1):  # noqa: ARG002
        reverse = direction == -1
        try:
            self._docs.sort(key=lambda d: d.get(field), reverse=reverse)
        except Exception:
            pass
        return self
    def __aiter__(self):
        async def _gen():
            for d in self._docs:
                yield d
        return _gen()


class _Col:
    def __init__(self):
        self._store = {}
    async def insert_one(self, payload):
        _id = payload.get("_id") or ObjectId()
        payload = {**payload, "_id": _id}
        self._store[_id] = payload
        class _Res:
            inserted_id = _id
        return _Res()
    async def find_one(self, q, *_, **__):
        if "username" in q:
            for v in self._store.values():
                if v.get("username") == q["username"]:
                    return v
            return None
        if "_id" in q:
            return self._store.get(q["_id"]) or None
        return None
    def find(self, q=None, projection=None):  # noqa: ARG002
        docs = list(self._store.values())
        # handle simple $in
        if q and isinstance(q, dict) and "_id" in q and isinstance(q["_id"], dict) and "$in" in q["_id"]:
            ids = {x for x in q["_id"]["$in"]}
            docs = [d for d in docs if d.get("_id") in ids]
        # projection include
        if projection:
            keys = {k for k, v in projection.items() if v}
            _docs = []
            for d in docs:
                _docs.append({k: d[k] for k in keys if k in d})
            docs = _docs
        return _Cursor(docs)


class _DB:
    def __init__(self):
        self.users = _Col()
        self.roles = _Col()


@pytest.mark.asyncio
async def test_rbac_repo_user_crud_and_role_queries():
    db = _DB()
    repo = RbacRepository(db)

    now = datetime.now()

    # Create roles
    r1 = Role(_id=None, role_name="Admin", description=None, created_at=now)
    r2 = Role(_id=None, role_name="Viewer", description=None, created_at=now)
    r1_out = await repo.create_role(r1)
    r2_out = await repo.create_role(r2)
    assert isinstance(r1_out.id, str) and isinstance(r2_out.id, str)

    # List role names by ids
    names = await repo.list_role_names([r1_out.id, r2_out.id])
    assert set(names) == {"Admin", "Viewer"}

    # Get roles by ids and list roles (sorted by name)
    roles = await repo.get_roles_by_ids([r1_out.id, r2_out.id])
    assert {x.role_name for x in roles} == {"Admin", "Viewer"}

    all_roles = await repo.list_roles()
    assert [x.role_name for x in all_roles] == ["Admin", "Viewer"]

    # Create user
    u = User(
        _id=None,
        username="jdoe",
        full_name="Jane Doe",
        email="jdoe@example.com",
        password_hash="hash",
        role_ids=[r1_out.id],
        assigned_squad_ids=[],
        created_at=now,
    )
    u_out = await repo.create_user(u)
    assert isinstance(u_out.id, str)
    assert u_out.username == "jdoe"

    # find by username
    fu = await repo.find_user_by_username("jdoe")
    assert fu and fu.username == "jdoe"

    # find by id
    fu2 = await repo.find_user_by_id(u_out.id)
    assert fu2 and fu2.id == u_out.id

    # get role by id
    g1 = await repo.get_role_by_id(r1_out.id)
    assert g1 and g1.role_name == "Admin"
