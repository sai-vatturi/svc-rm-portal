from datetime import datetime
import pytest

from bson import ObjectId

from app.services.release_service import ReleaseService
from app.models.release import (
    ReleaseProduct,
    ReleaseProductQualityGate,
    ReleaseMilestone,
    ReleaseChange,
)


class _ReleasesCol:
    def __init__(self, docs):
        # store by ObjectId
        self._store = {d["_id"]: d for d in docs}
    async def find_one(self, q):
        _id = q.get("_id")
        return self._store.get(_id)
    async def update_one(self, q, update, array_filters=None):  # noqa: ARG002
        _id = q.get("_id")
        doc = self._store.get(_id)
        class _Res:
            matched_count = 0
            modified_count = 0
        if not doc:
            return _Res()
        _Res.matched_count = 1
        # handle $push and $set
        if "$push" in update:
            path, value = next(iter(update["$push"].items()))
            if path == "products":
                doc.setdefault("products", []).append(value)
                _Res.modified_count = 1
            elif path.startswith("products.$[p].quality_gates"):
                # Could be gate or milestone
                if path.endswith("quality_gates"):
                    # add gate to product
                    product_id = None
                    for f in (array_filters or []):
                        if "p.product_id" in f:
                            product_id = f["p.product_id"]
                    if product_id is None:
                        return _Res()
                    for p in doc.setdefault("products", []):
                        if p.get("product_id") == product_id:
                            p.setdefault("quality_gates", []).append(value)
                            _Res.modified_count = 1
                            break
                elif path.endswith("milestones"):
                    # add milestone to a specific gate of a product
                    product_id = None
                    gate_name = None
                    for f in (array_filters or []):
                        if "p.product_id" in f:
                            product_id = f["p.product_id"]
                        if "g.gate_name" in f:
                            gate_name = f["g.gate_name"]
                    if product_id is None or gate_name is None:
                        return _Res()
                    for p in doc.setdefault("products", []):
                        if p.get("product_id") == product_id:
                            for g in p.setdefault("quality_gates", []):
                                if g.get("gate_name") == gate_name:
                                    g.setdefault("milestones", []).append(value)
                                    _Res.modified_count = 1
                                    break
            return _Res()
        if "$set" in update:
            for k, v in update["$set"].items():
                doc[k] = v
            _Res.modified_count = 1
        return _Res()


class _DB:
    def __init__(self, releases):
        self.releases = releases


@pytest.mark.asyncio
async def test_release_service_get_and_mutations(monkeypatch):
    now = datetime.now()
    rid = ObjectId()
    base_doc = {
        "_id": rid,
        "release_id": "REL-1",
        "release_name": "R1",
        "release_date": now,
        "created_at": now,
        "products": [],
    }

    releases_col = _ReleasesCol([base_doc])

    def _fake_get_db():
        return _DB(releases_col)

    # Patch get_db used by ReleaseService
    monkeypatch.setattr("app.services.release_service.get_db", _fake_get_db)

    svc = ReleaseService()

    # get
    out = await svc.get(str(rid))
    assert out is not None
    assert out.id == str(rid)
    assert out.release_name == "R1"

    # add product
    prod = ReleaseProduct(application_id="app1", product_id="p1")
    mc = await svc.add_product(str(rid), prod)
    assert mc == 1
    assert len(releases_col._store[rid]["products"]) == 1

    # add gate
    gate = ReleaseProductQualityGate(gate_name="QA")
    mc2 = await svc.add_gate(str(rid), "p1", gate)
    assert mc2 == 1
    prodd = releases_col._store[rid]["products"][0]
    assert len(prodd.get("quality_gates", [])) == 1

    # add milestone
    ms = ReleaseMilestone(milestone_key="MS1", milestone_name="UAT")
    mc3 = await svc.add_milestone(str(rid), "p1", "QA", ms)
    assert mc3 == 1
    gates = prodd.get("quality_gates", [])
    assert len(gates[0].get("milestones", [])) == 1

    # upsert change
    ch = ReleaseChange(change_id="CHG-1")
    mc4 = await svc.upsert_change(str(rid), ch)
    assert mc4 == 1
    assert releases_col._store[rid]["chg"]["change_id"] == "CHG-1"
