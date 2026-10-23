from types import SimpleNamespace
from uuid import uuid4


def _authorize_senotype_reads(monkeypatch):
    ingest_service = SimpleNamespace(
        get_senotype_privs=lambda token: {"has_senotype_publish": True}
    )
    monkeypatch.setattr("common.decorator.get_ingest_api_service", lambda: ingest_service)


def test_get_senotype(app, database, monkeypatch):
    # Insert a test senotype into the database
    senotype = {"uuid": uuid4().hex, "title": "Example"}
    collection = database["sennet"]["senotypes"]
    collection.insert_one(dict(senotype))
    _authorize_senotype_reads(monkeypatch)

    try:
        with app.test_client() as client:
            res = client.get(
                f"/senotypes/{senotype['uuid']}",
                headers={"Authorization": "Bearer test-token"},
            )

        assert res.status_code == 200
        assert res.json == {"senotype": senotype}
    finally:
        collection.delete_one({"uuid": senotype["uuid"]})


def test_get_missing_senotype(app, monkeypatch):
    # Use a UUID that does not exist in the database
    uuid = uuid4().hex
    _authorize_senotype_reads(monkeypatch)

    with app.test_client() as client:
        res = client.get(
            f"/senotypes/{uuid}",
            headers={"Authorization": "Bearer test-token"},
        )

    assert res.status_code == 404
    assert res.json == {"message": "Senotype not found"}


def test_get_senotype_unauthenticated(app):
    with app.test_client() as client:
        res = client.get(f"/senotypes/{uuid4().hex}")

    assert res.status_code == 401
    assert res.json == {"message": "Missing or invalid Authorization header"}


def test_get_senotypes_returns_results(app, database, monkeypatch):
    dataset_uuid = uuid4().hex
    senotypes = [
        {"uuid": uuid4().hex, "dataset": {"uuid": dataset_uuid}},
        {"uuid": uuid4().hex, "dataset": {"uuid": dataset_uuid}},
    ]
    collection = database["sennet"]["senotypes"]
    collection.insert_many([dict(senotype) for senotype in senotypes])
    _authorize_senotype_reads(monkeypatch)

    try:
        with app.test_client() as client:
            res = client.get(
                f"/senotypes?dataset_uuid={dataset_uuid}",
                headers={"Authorization": "Bearer test-token"},
            )

        assert res.status_code == 200
        assert {senotype["uuid"] for senotype in res.json["senotypes"]} == {
            senotype["uuid"] for senotype in senotypes
        }
        assert res.json["pagination"]["total"] == 2
    finally:
        collection.delete_many({"uuid": {"$in": [senotype["uuid"] for senotype in senotypes]}})


def test_get_senotypes_returns_no_results(app, monkeypatch):
    dataset_uuid = uuid4().hex
    _authorize_senotype_reads(monkeypatch)

    with app.test_client() as client:
        res = client.get(
            f"/senotypes?dataset_uuid={dataset_uuid}",
            headers={"Authorization": "Bearer test-token"},
        )

    assert res.status_code == 200
    assert res.json == {
        "senotypes": [],
        "pagination": {"total": 0, "limit": 25, "offset": 0, "order": "asc"},
    }


def test_get_senotypes_filters_by_dataset(app, database, monkeypatch):
    dataset_uuid = uuid4().hex
    other_dataset_uuid = uuid4().hex
    senotypes = [
        {"uuid": uuid4().hex, "dataset": {"uuid": dataset_uuid}, "created_timestamp": 1},
        {"uuid": uuid4().hex, "dataset": {"uuid": dataset_uuid}, "created_timestamp": 2},
        {"uuid": uuid4().hex, "dataset": {"uuid": other_dataset_uuid}, "created_timestamp": 3},
    ]
    collection = database["sennet"]["senotypes"]
    collection.insert_many([dict(senotype) for senotype in senotypes])
    _authorize_senotype_reads(monkeypatch)

    try:
        with app.test_client() as client:
            res = client.get(
                f"/senotypes?dataset_uuid={dataset_uuid}",
                headers={"Authorization": "Bearer test-token"},
            )

        assert res.status_code == 200
        assert [senotype["uuid"] for senotype in res.json["senotypes"]] == [
            senotypes[0]["uuid"],
            senotypes[1]["uuid"],
        ]
        assert res.json["pagination"]["total"] == 2
    finally:
        collection.delete_many({"uuid": {"$in": [senotype["uuid"] for senotype in senotypes]}})


def test_get_senotypes_paginates_results(app, database, monkeypatch):
    dataset_uuid = uuid4().hex
    senotypes = [
        {"uuid": uuid4().hex, "dataset": {"uuid": dataset_uuid}, "created_timestamp": index}
        for index in range(1, 4)
    ]
    collection = database["sennet"]["senotypes"]
    collection.insert_many([dict(senotype) for senotype in senotypes])
    _authorize_senotype_reads(monkeypatch)

    try:
        with app.test_client() as client:
            res = client.get(
                f"/senotypes?dataset_uuid={dataset_uuid}&limit=1&offset=1&order=desc",
                headers={"Authorization": "Bearer test-token"},
            )

        assert res.status_code == 200
        assert [senotype["uuid"] for senotype in res.json["senotypes"]] == [senotypes[1]["uuid"]]
        assert res.json["pagination"] == {
            "total": 3,
            "limit": 1,
            "offset": 1,
            "order": "desc",
        }
    finally:
        collection.delete_many({"uuid": {"$in": [senotype["uuid"] for senotype in senotypes]}})
