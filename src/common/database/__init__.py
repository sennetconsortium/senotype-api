from pymongo.collection import Collection

from common.context import get_mongo_db


def get_collection(name: str) -> Collection:
    db = get_mongo_db()
    return db[name]
