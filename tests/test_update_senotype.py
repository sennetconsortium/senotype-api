from types import SimpleNamespace
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
UPDATE_REQUEST = {
    "title": "Updated senotype",
    "description": "Updated description",
    "taxon": ["NCBI:9606"],
    "organ": ["UBERON:0002048"],
    "cell_type": ["CL:0000000"],
    "hallmark": ["SENOTYPE_VS:C00201"],
}
UPDATED_FIELDS = {
    "title": "Updated senotype",
    "description": "Updated description",
}


@pytest.mark.parametrize(
    ("privilege", "owner_sub"),
    [("has_senotype_edit", TOKEN_DATA["sub"]), ("has_senotype_curate", "another-user")],
    ids=["owner-editor", "curator-updates-other-owner"],
)
def test_update_senotype_success(app, database, monkeypatch, privilege, owner_sub):
    senotype_uuid = uuid4().hex
    collection = database["sennet"]["senotypes"]
    original = insert_test_senotype(collection, senotype_uuid, owner_sub)
    mock_senotype_auth(
        monkeypatch,
        token_data=TOKEN_DATA,
        privileges={privilege: True},
    )
    validate_request = Mock(return_value=(UPDATED_FIELDS, {}))
    reindex_senotype = Mock()
    monkeypatch.setattr("routes.senotypes.validate_senotype_request", validate_request)
    monkeypatch.setattr(
        "routes.senotypes.get_search_api_service",
        lambda: SimpleNamespace(reindex_senotype=reindex_senotype),
    )

    try:
        with app.test_client() as client:
            res = client.put(
                f"/senotypes/{senotype_uuid}",
                json=UPDATE_REQUEST,
                headers={"Authorization": "Bearer test-token"},
            )

        assert res.status_code == 200
        updated = res.json["senotype"]
        assert updated["title"] == UPDATED_FIELDS["title"]
        assert updated["description"] == UPDATED_FIELDS["description"]
        assert updated["uuid"] == original["uuid"]
        assert updated["sennet_id"] == original["sennet_id"]
        assert updated["created_by_user_sub"] == original["created_by_user_sub"]
        assert updated["created_timestamp"] == original["created_timestamp"]
        assert collection.find_one({"uuid": senotype_uuid})["title"] == UPDATED_FIELDS["title"]
        validate_request.assert_called_once()
        reindex_senotype.assert_called_once_with(senotype_uuid, token="test-token")
    finally:
        collection.delete_one({"uuid": senotype_uuid})


def test_update_senotype_without_return_dict(app, database, monkeypatch):
    senotype_uuid = uuid4().hex
    collection = database["sennet"]["senotypes"]
    insert_test_senotype(collection, senotype_uuid, TOKEN_DATA["sub"])
    mock_senotype_auth(
        monkeypatch,
        token_data=TOKEN_DATA,
        privileges={"has_senotype_edit": True},
    )
    monkeypatch.setattr(
        "routes.senotypes.validate_senotype_request",
        Mock(return_value=(UPDATED_FIELDS, {})),
    )
    reindex_senotype = Mock()
    monkeypatch.setattr(
        "routes.senotypes.get_search_api_service",
        lambda: SimpleNamespace(reindex_senotype=reindex_senotype),
    )

    try:
        with app.test_client() as client:
            res = client.put(
                f"/senotypes/{senotype_uuid}?return_dict=false",
                json=UPDATE_REQUEST,
                headers={"Authorization": "Bearer test-token"},
            )

        assert res.status_code == 200
        assert res.json == {"message": "Senotype updated"}
        assert collection.find_one({"uuid": senotype_uuid})["title"] == UPDATED_FIELDS["title"]
        reindex_senotype.assert_called_once_with(senotype_uuid, token="test-token")
    finally:
        collection.delete_one({"uuid": senotype_uuid})


def test_update_senotype_non_owner_is_forbidden(app, database, monkeypatch):
    senotype_uuid = uuid4().hex
    collection = database["sennet"]["senotypes"]
    insert_test_senotype(collection, senotype_uuid, "original-owner")
    mock_senotype_auth(
        monkeypatch,
        token_data=TOKEN_DATA,
        privileges={"has_senotype_edit": True},
    )
    validate_request = Mock()
    monkeypatch.setattr("routes.senotypes.validate_senotype_request", validate_request)

    try:
        with app.test_client() as client:
            res = client.put(
                f"/senotypes/{senotype_uuid}",
                json=UPDATE_REQUEST,
                headers={"Authorization": "Bearer test-token"},
            )

        assert res.status_code == 403
        assert res.json == {"message": "You do not have permission to update this senotype"}
        validate_request.assert_not_called()
        assert collection.find_one({"uuid": senotype_uuid})["title"] == "Original title"
    finally:
        collection.delete_one({"uuid": senotype_uuid})


def test_update_missing_senotype_returns_not_found(app, monkeypatch):
    mock_senotype_auth(
        monkeypatch,
        token_data=TOKEN_DATA,
        privileges={"has_senotype_edit": True},
    )
    validate_request = Mock()
    monkeypatch.setattr("routes.senotypes.validate_senotype_request", validate_request)

    with app.test_client() as client:
        res = client.put(
            f"/senotypes/{uuid4().hex}",
            json=UPDATE_REQUEST,
            headers={"Authorization": "Bearer test-token"},
        )

    assert res.status_code == 404
    assert res.json == {"message": "Senotype not found"}
    validate_request.assert_not_called()


def test_update_senotype_without_group_is_forbidden(app, monkeypatch):
    mock_senotype_auth(monkeypatch, token_data=TOKEN_DATA, privileges={})

    with app.test_client() as client:
        res = client.put(
            f"/senotypes/{uuid4().hex}",
            json={},
            headers={"Authorization": "Bearer test-token"},
        )

    assert res.status_code == 403
    assert res.json == {
        "message": "User does not have senotype group membership: " "senotype_curate, senotype_edit"
    }


def test_update_senotype_invalid_body_skips_validation(app, monkeypatch):
    mock_senotype_auth(
        monkeypatch,
        token_data=TOKEN_DATA,
        privileges={"has_senotype_edit": True},
    )
    validate_request = Mock()
    monkeypatch.setattr("routes.senotypes.validate_senotype_request", validate_request)

    with app.test_client() as client:
        res = client.put(
            f"/senotypes/{uuid4().hex}",
            json={},
            headers={"Authorization": "Bearer test-token"},
        )

    assert res.status_code == 400
    assert res.json["message"] == "Validation error"
    validate_request.assert_not_called()


def test_update_senotype_semantic_validation_error_does_not_update(app, database, monkeypatch):
    senotype_uuid = uuid4().hex
    collection = database["sennet"]["senotypes"]
    insert_test_senotype(collection, senotype_uuid, TOKEN_DATA["sub"])
    mock_senotype_auth(
        monkeypatch,
        token_data=TOKEN_DATA,
        privileges={"has_senotype_edit": True},
    )
    validate_request = Mock(return_value=({}, {"title": ["Invalid title"]}))
    monkeypatch.setattr("routes.senotypes.validate_senotype_request", validate_request)

    try:
        with app.test_client() as client:
            res = client.put(
                f"/senotypes/{senotype_uuid}",
                json=UPDATE_REQUEST,
                headers={"Authorization": "Bearer test-token"},
            )

        assert res.status_code == 400
        assert res.json == {
            "message": "Validation error",
            "errors": {"title": ["Invalid title"]},
        }
        validate_request.assert_called_once()
        assert collection.find_one({"uuid": senotype_uuid})["title"] == "Original title"
    finally:
        collection.delete_one({"uuid": senotype_uuid})
