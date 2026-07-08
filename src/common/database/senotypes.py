from common.database import get_collection


def find_senotypes(limit: int | None = None, offset: int = 0) -> tuple[list[dict], int]:
    collection = get_collection("senotypes")
    total = collection.count_documents({})
    cursor = collection.find({}, {"_id": 0}).skip(offset)  # exclude the MongoDB _id field
    if limit is not None:
        cursor = cursor.limit(limit)
    docs = [doc for doc in cursor]
    return docs, total


def find_senotype(uuid: str) -> dict | None:
    collection = get_collection("senotypes")
    doc = collection.find_one({"uuid": uuid}, {"_id": 0})  # exclude the MongoDB _id field
    if doc is None:
        return None
    return doc


def insert_senotype(senotype: dict) -> dict:
    collection = get_collection("senotypes")
    collection.insert_one(senotype)
    doc = collection.find_one({"uuid": senotype["uuid"]}, {"_id": 0})
    if doc is None:
        raise Exception("Failed to retrieve inserted senotype")
    return doc


def update_senotype(uuid: str, senotype: dict) -> dict | None:
    collection = get_collection("senotypes")
    doc = collection.find_one_and_update(
        {"uuid": uuid},
        {"$set": senotype},
        projection={"_id": 0},
        return_document=True,
    )
    if doc is None:
        return None

    return doc


def delete_senotype(sennet_id: str) -> bool:
    collection = get_collection("senotypes")
    result = collection.delete_one({"sennet_id": sennet_id})
    return result.deleted_count > 0
