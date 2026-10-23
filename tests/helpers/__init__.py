import os
from unittest.mock import Mock

import pytest

from main import create_app


def mock_senotype_auth(monkeypatch, token_data=None, privileges=None):
    ingest_service = Mock()
    ingest_service.get_senotype_privs.return_value = (
        privileges if privileges is not None else {"has_senotype_publish": True}
    )
    if token_data is not None:
        ingest_service.get_token_info.return_value = token_data
    monkeypatch.setattr("common.decorator.get_ingest_api_service", lambda: ingest_service)
    return ingest_service


def insert_test_senotype(collection, uuid, created_by_user_sub):
    senotype = {
        "uuid": uuid,
        "sennet_id": "SNT123.ABCD.456",
        "created_by_user_displayname": "Original Owner",
        "created_by_user_email": "owner@example.org",
        "created_by_user_sub": created_by_user_sub,
        "created_timestamp": 1,
        "last_modified_user_displayname": "Original Owner",
        "last_modified_user_email": "owner@example.org",
        "last_modified_user_sub": created_by_user_sub,
        "last_modified_timestamp": 1,
        "title": "Original title",
        "description": "Original description",
    }
    collection.insert_one(dict(senotype))
    return senotype


@pytest.fixture()
def app(database, monkeypatch):
    config_file = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "config", "app.test.cfg")
    )
    monkeypatch.setenv("SENOTYPE_CONFIG_FILE", config_file)

    app = create_app()
    app.config.update({"TESTING": True})

    # other setup
    yield app
    # cleanup
