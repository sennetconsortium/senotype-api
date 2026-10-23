import os
from unittest.mock import Mock

import pytest

from main import create_app


def mock_senotype_auth(monkeypatch, token_data=None):
    ingest_service = Mock()
    ingest_service.get_senotype_privs.return_value = {"has_senotype_publish": True}
    if token_data is not None:
        ingest_service.get_token_info.return_value = token_data
    monkeypatch.setattr("common.decorator.get_ingest_api_service", lambda: ingest_service)
    return ingest_service


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
