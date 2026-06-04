import time

import pytest
from pymongo import MongoClient


def wait_for_mongodb(timeout=60):
    mongo_client = MongoClient(
        host="localhost",
        port=27017,
        username="test_user",
        password="test_password",
        authSource="sennet",
    )

    start_time = time.time()
    while True:
        try:
            mongo_client.admin.command("ping")
            print("MongoDB is up and running")
            break
        except Exception as e:
            if time.time() - start_time > timeout:
                print("Timeout waiting for MongoDB to be ready")
                raise e

            print("Waiting for MongoDB to be ready...")
            time.sleep(1)

    return mongo_client


@pytest.fixture(scope="session")
def database():
    client = wait_for_mongodb()

    yield client

    client.close()
