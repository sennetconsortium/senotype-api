from typing import Optional

from pydantic import BaseModel

from common.database import get_collection


class Valueset(BaseModel):
    code: str
    term: str
    predicate_term: str
    predicate_iri: Optional[str] = None


def find_valuesets(predicate_term: str | None = None) -> list[Valueset]:
    collection = get_collection("valuesets")
    query = {}
    if predicate_term is not None:
        query["predicate_term"] = predicate_term
    docs = collection.find(query, {"_id": 0})  # exclude the MongoDB _id field
    return [Valueset.model_validate(doc) for doc in docs]


def find_valueset(code: str) -> Valueset | None:
    collection = get_collection("valuesets")
    doc = collection.find_one({"code": code}, {"_id": 0})  # exclude the MongoDB _id field
    if doc is None:
        return None
    return Valueset.model_validate(doc)
