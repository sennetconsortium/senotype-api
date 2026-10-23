import os

import pytest

from main import create_app


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
