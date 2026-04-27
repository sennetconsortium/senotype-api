from typing import Literal
from uuid import UUID

from pydantic import BaseModel, HttpUrl, SecretStr


class AppConfig(BaseModel):
    GLOBUS_APP_CLIENT_ID: str
    GLOBUS_APP_CLIENT_SECRET: SecretStr
    GLOBUS_GROUP_UUIDS: dict[str, UUID]
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    MONGO_DB_NAME: str
    MONGO_HOST: str
    MONGO_USERNAME: str
    MONGO_PASSWORD: SecretStr
    ENTITY_API_URL: HttpUrl
    SEARCH_API_URL: HttpUrl
    UBKG_API_URL: HttpUrl
    UUID_API_URL: HttpUrl
    EUTILS_API_URL: HttpUrl
    SCICRUNCH_API_URL: HttpUrl
