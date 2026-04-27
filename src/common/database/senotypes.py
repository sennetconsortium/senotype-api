from common.database import get_collection


def find_senotypes() -> list[dict]:
    collection = get_collection("senotypes")
    docs = collection.find({}, {"_id": 0})  # exclude the MongoDB _id field
    return [doc for doc in docs]


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
