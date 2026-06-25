import pytest

from main import create_app


@pytest.fixture()
def app(database):
    app = create_app()
    app.config.update({"TESTING": True})

    # other setup
    yield app
    # cleanup
