from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from tests.helpers import mock_senotype_auth


@pytest.mark.parametrize("return_dict", [True, False], ids=["returns-senotype", "no-return-dict"])
def test_create_senotype(app, database, monkeypatch, return_dict):
    created_uuid = uuid4().hex
    sennet_id = "SNT123.ABCD.456"
    token_data = {
        "email": "test@example.org",
        "name": "Test User",
        "sub": "test-user-sub",
        "username": "test-user",
    }
    mock_senotype_auth(monkeypatch, token_data=token_data)
    ubkg_service = SimpleNamespace(
        get_organs=Mock(return_value=[{"organ_uberon": "UBERON:0002048", "term": "lung"}]),
        get_celltypes=Mock(
            return_value=[
                {
                    "cell_type": {
                        "id": "CL:0000000",
                        "name": "test cell",
                        "definition": "A test cell type",
                    }
                }
            ]
        ),
    )
    create_uuid = Mock(return_value=[{"uuid": created_uuid, "sennet_id": sennet_id}])
    reindex_senotype = Mock()
    search_service = SimpleNamespace(reindex_senotype=reindex_senotype)

    monkeypatch.setattr("common.validation.senotype.get_ubkg_api_service", lambda: ubkg_service)
    monkeypatch.setattr(
        "common.validation.senotype.get_entity_api_service", lambda: SimpleNamespace()
    )
    monkeypatch.setattr(
        "common.validation.senotype.get_scicrunch_api_service", lambda: SimpleNamespace()
    )
    monkeypatch.setattr(
        "routes.senotypes.get_uuid_api_service",
        lambda: SimpleNamespace(create_uuid=create_uuid),
    )
    monkeypatch.setattr("routes.senotypes.get_search_api_service", lambda: search_service)

    request_body = {
        "title": "Example senotype",
        "description": "A senotype created by a route test",
        "taxon": ["NCBI:9606"],
        "organ": ["UBERON:0002048"],
        "cell_type": ["CL:0000000"],
        "hallmark": ["SENOTYPE_VS:C00201"],
    }
    collection = database["sennet"]["senotypes"]

    try:
        with app.test_client() as client:
            res = client.post(
                "/senotypes" if return_dict else "/senotypes?return_dict=false",
                json=request_body,
                headers={"Authorization": "Bearer test-token"},
            )

        assert res.status_code == 201
        if return_dict:
            created = res.json["senotype"]
            assert created["uuid"] == created_uuid
            assert created["sennet_id"] == sennet_id
            assert created["title"] == request_body["title"]
            assert created["description"] == request_body["description"]
            assert created["created_by_user_sub"] == token_data["sub"]
        else:
            assert res.json == {"message": "Senotype created"}

        assert collection.find_one({"uuid": created_uuid}) is not None
        create_uuid.assert_called_once_with({"entity_type": "REFERENCE"}, "test-token")
        reindex_senotype.assert_called_once_with(created_uuid, token="test-token")
    finally:
        collection.delete_one({"uuid": created_uuid})


def test_create_senotype_without_group(app, monkeypatch):
    ingest_service = mock_senotype_auth(monkeypatch)
    ingest_service.get_senotype_privs.return_value = {}

    with app.test_client() as client:
        res = client.post(
            "/senotypes",
            json={},
            headers={"Authorization": "Bearer test-token"},
        )

    assert res.status_code == 403
    assert res.json == {
        "message": "User does not have senotype group membership: "
        "senotype_curate, senotype_edit, senotype_publish"
    }


def test_create_senotype_invalid_body_skips_validation_services(app, monkeypatch):
    token_data = {
        "email": "test@example.org",
        "name": "Test User",
        "sub": "test-user-sub",
        "username": "test-user",
    }
    mock_senotype_auth(monkeypatch, token_data=token_data)
    validate_request = Mock()
    monkeypatch.setattr("routes.senotypes.validate_senotype_request", validate_request)

    with app.test_client() as client:
        res = client.post(
            "/senotypes",
            json={},
            headers={"Authorization": "Bearer test-token"},
        )

    assert res.status_code == 400
    assert res.json["message"] == "Validation error"
    validate_request.assert_not_called()
