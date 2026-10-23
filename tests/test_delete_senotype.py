from unittest.mock import Mock
from uuid import uuid4

import pytest

from tests.helpers import insert_test_senotype, mock_senotype_auth

TOKEN_DATA = {
    "email": "editor@example.org",
    "name": "Editor",
    "sub": "editor-sub",
    "username": "editor",
}


@pytest.mark.parametrize(
    ("privilege", "owner_sub"),
    [("has_senotype_edit", TOKEN_DATA["sub"]), ("has_senotype_curate", "another-user")],
    ids=["owner-editor", "curator-deletes-other-owner"],
)
def test_delete_senotype_success(app, database, monkeypatch, privilege, owner_sub):
    senotype_uuid = uuid4().hex
    collection = database["sennet"]["senotypes"]
    insert_test_senotype(collection, senotype_uuid, owner_sub)
    mock_senotype_auth(
        monkeypatch,
        token_data=TOKEN_DATA,
        privileges={privilege: True},
    )

    try:
        with app.test_client() as client:
            res = client.delete(
                f"/senotypes/{senotype_uuid}",
                headers={"Authorization": "Bearer test-token"},
            )

        assert res.status_code == 200
        assert res.json == {"message": "Senotype deleted"}
        assert collection.find_one({"uuid": senotype_uuid}) is None
    finally:
        collection.delete_one({"uuid": senotype_uuid})


def test_delete_senotype_non_owner_is_forbidden(app, database, monkeypatch):
    senotype_uuid = uuid4().hex
    collection = database["sennet"]["senotypes"]
    insert_test_senotype(collection, senotype_uuid, "original-owner")
    mock_senotype_auth(
        monkeypatch,
        token_data=TOKEN_DATA,
        privileges={"has_senotype_edit": True},
    )

    try:
        with app.test_client() as client:
            res = client.delete(
                f"/senotypes/{senotype_uuid}",
                headers={"Authorization": "Bearer test-token"},
            )

        assert res.status_code == 403
        assert res.json == {"message": "You do not have permission to delete this senotype"}
        assert collection.find_one({"uuid": senotype_uuid}) is not None
    finally:
        collection.delete_one({"uuid": senotype_uuid})


def test_delete_missing_senotype_returns_not_found(app, monkeypatch):
    mock_senotype_auth(
        monkeypatch,
        token_data=TOKEN_DATA,
        privileges={"has_senotype_edit": True},
    )

    with app.test_client() as client:
        res = client.delete(
            f"/senotypes/{uuid4().hex}",
            headers={"Authorization": "Bearer test-token"},
        )

    assert res.status_code == 404
    assert res.json == {"message": "Senotype not found"}


def test_delete_senotype_disappears_after_lookup(app, database, monkeypatch):
    senotype_uuid = uuid4().hex
    collection = database["sennet"]["senotypes"]
    insert_test_senotype(collection, senotype_uuid, TOKEN_DATA["sub"])
    mock_senotype_auth(
        monkeypatch,
        token_data=TOKEN_DATA,
        privileges={"has_senotype_edit": True},
    )

    def delete_after_lookup(uuid):
        collection.delete_one({"uuid": uuid})
        return False

    delete_senotype = Mock(side_effect=delete_after_lookup)
    monkeypatch.setattr("routes.senotypes.delete_db_senotype", delete_senotype)

    try:
        with app.test_client() as client:
            res = client.delete(
                f"/senotypes/{senotype_uuid}",
                headers={"Authorization": "Bearer test-token"},
            )

        assert res.status_code == 404
        assert res.json == {"message": "Senotype not found"}
        delete_senotype.assert_called_once_with(senotype_uuid)
        assert collection.find_one({"uuid": senotype_uuid}) is None
    finally:
        collection.delete_one({"uuid": senotype_uuid})


def test_delete_senotype_without_group_is_forbidden(app, monkeypatch):
    mock_senotype_auth(monkeypatch, token_data=TOKEN_DATA, privileges={})

    with app.test_client() as client:
        res = client.delete(
            f"/senotypes/{uuid4().hex}",
            headers={"Authorization": "Bearer test-token"},
        )

    assert res.status_code == 403
    assert res.json == {
        "message": "User does not have senotype group membership: " "senotype_curate, senotype_edit"
    }
