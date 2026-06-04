import json
import time
from pathlib import Path

import pytest
from pymongo import MongoClient


def wait_for_mongodb(timeout=60):
    # Connect as admin (no auth needed before user is created)
    mongo_client = MongoClient(host="localhost", port=27017)

    start_time = time.time()
    while True:
        try:
            mongo_client.admin.command("ping")
            print("MongoDB is up and running")
            break
        except Exception as e:
            if time.time() - start_time > timeout:
                raise e
            print("Waiting for MongoDB to be ready...")
            time.sleep(1)

    return mongo_client


@pytest.fixture(scope="session")
def database():
    admin_client = wait_for_mongodb()
    db = admin_client["sennet"]

    # Create user if it doesn't exist
    existing_users = db.command("usersInfo", "test_user")
    if not existing_users["users"]:
        db.command(
            "createUser",
            "test_user",
            pwd="test_password",
            roles=[{"role": "readWrite", "db": "sennet"}],
        )

    # Seed data if collections are empty
    data_dir = Path(__file__).parent.parent / "data"
    for json_file in data_dir.glob("*.json"):
        collection_name = json_file.stem
        if db[collection_name].count_documents({}) == 0:
            documents = json.loads(json_file.read_text())
            db[collection_name].insert_many(documents)

    auth_client = MongoClient(
        host="localhost",
        port=27017,
        username="test_user",
        password="test_password",
        authSource="sennet",
    )

    yield auth_client

    auth_client.close()
    admin_client.close()
