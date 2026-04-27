import logging
from uuid import UUID

from flask import current_app
from globus_sdk import ConfidentialAppAuthClient
from pymongo.database import Database

from common.service.entity import EntityAPIService
from common.service.eutils import EUtilsAPIService
from common.service.scicrunch import SciCrunchAPIService
from common.service.search import SearchAPIService
from common.service.ubkg import UBKGAPIService
from common.service.uuid import UUIDAPIService


def get_logger() -> logging.Logger:
    return current_app.logger


def get_auth_client() -> ConfidentialAppAuthClient:
    return current_app.extensions["auth_client"]


def get_mongo_db() -> Database:
    return current_app.extensions["mongo_db"]


def get_globus_group_uuids() -> dict[str, UUID]:
    return current_app.extensions["app_config"].GLOBUS_GROUP_UUIDS


def get_search_api_service() -> SearchAPIService:
    base_url = str(current_app.extensions["app_config"].SEARCH_API_URL)
    return SearchAPIService(base_url=base_url)


def get_ubkg_api_service() -> UBKGAPIService:
    base_url = str(current_app.extensions["app_config"].UBKG_API_URL)
    return UBKGAPIService(base_url=base_url)


def get_entity_api_service() -> EntityAPIService:
    base_url = str(current_app.extensions["app_config"].ENTITY_API_URL)
    return EntityAPIService(base_url=base_url)


def get_uuid_api_service() -> UUIDAPIService:
    base_url = str(current_app.extensions["app_config"].UUID_API_URL)
    return UUIDAPIService(base_url=base_url)


def get_eutils_api_service() -> EUtilsAPIService:
    base_url = str(current_app.extensions["app_config"].EUTILS_API_URL)
    return EUtilsAPIService(base_url=base_url)


def get_scicrunch_api_service() -> SciCrunchAPIService:
    base_url = str(current_app.extensions["app_config"].SCICRUNCH_API_URL)
    return SciCrunchAPIService(base_url=base_url)
