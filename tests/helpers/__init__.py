import pytest

from main import create_app


@pytest.fixture()
@pytest.mark.usefixtures("database")
def app():
    app = create_app()
    app.config.update({"TESTING": True})

    # other setup
    yield app
    # cleanup
