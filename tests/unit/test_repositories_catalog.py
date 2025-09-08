from datetime import datetime
import pytest

from app.repositories.catalog_repo import CatalogRepository
from app.models.catalog import Application, Squad, JiraBoard


@pytest.mark.asyncio
async def test_catalog_repo_create_and_list():
    now = datetime.now().isoformat() + "Z"

    class _Col:
        def __init__(self):
            self._docs = []
        async def insert_one(self, data):  # store as-is
            self._docs.append({**data, "_id": "id"})
            class _Res:
                inserted_id = "id"
            return _Res()
        def find(self):
            class _Cursor:
                def __init__(self, docs):
                    self._docs = docs
                def sort(self, *_):
                    return self
                def __aiter__(self):
                    async def _gen():
                        for d in self._docs:
                            yield d
                    return _gen()
            return _Cursor(self._docs)

    class _DB:
        applications = _Col(); squads = _Col(); jiraboards = _Col()

    repo = CatalogRepository(_DB())

    app = Application(_id=None, application_id="A1", application_name="App", technologies=[], products=[])
    out_app = await repo.create_application(app)
    assert out_app.application_id == "A1"

    squad = Squad(_id=None, squad_id="S1", squad_name="Team", squad_jira_board_ids=[], member_ids=[])
    out_squad = await repo.create_squad(squad)
    assert out_squad.squad_id == "S1"

    board = JiraBoard(_id=None, board_id="B1", board_name="Board")
    out_board = await repo.create_board(board)
    assert out_board.board_id == "B1"

    la = await repo.list_applications()
    ls = await repo.list_squads()
    lb = await repo.list_boards()
    assert len(la) == len(ls) == len(lb) == 1
