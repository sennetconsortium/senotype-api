from datetime import datetime

from bson.codec_options import TypeDecoder
from pymongo.collection import Collection

from common.context import get_mongo_db


def get_collection(name: str) -> Collection:
    db = get_mongo_db()
    return db[name]


class DatetimeDecoder(TypeDecoder):
    bson_type = datetime  # type: ignore

    def transform_bson(self, value: datetime) -> int:
        return int(value.timestamp() * 1000)
