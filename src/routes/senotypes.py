from datetime import datetime, timezone

from flask import Blueprint, current_app, request

from common.context import get_search_api_service, get_uuid_api_service
from common.database.senotypes import delete_senotype as delete_db_senotype
from common.database.senotypes import find_senotype, find_senotypes, insert_senotype
from common.database.senotypes import update_senotype as update_db_senotype
from common.decorator import (
    ALL_SENOTYPE_GROUPS,
    SenotypeGroup,
    TokenInfo,
    require_any_senotype_group,
    validate_body,
)
from common.validation.senotype import SenotypeRequest, validate_senotype_request

senotypes_bp = Blueprint("senotypes", __name__)


DEFAULT_SENOTYPES_LIMIT = 25
MAX_SENOTYPES_LIMIT = 100
VALID_SENOTYPES_ORDERS = ("asc", "desc")


@senotypes_bp.route("/senotypes", methods=["GET"])
@require_any_senotype_group(ALL_SENOTYPE_GROUPS)
def get_senotypes():
    try:
        limit = int(request.args.get("limit", DEFAULT_SENOTYPES_LIMIT))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return {"message": "limit and offset must be integers"}, 400

    order = request.args.get("order", "asc")

    if limit < 1 or limit > MAX_SENOTYPES_LIMIT:
        return {"message": f"limit must be between 1 and {MAX_SENOTYPES_LIMIT}"}, 400
    if offset < 0:
        return {"message": "offset must be non-negative"}, 400
    if order not in VALID_SENOTYPES_ORDERS:
        return {"message": f"order must be one of: {', '.join(VALID_SENOTYPES_ORDERS)}"}, 400

    senotypes, total = find_senotypes(limit=limit, offset=offset, order=order)
    return {
        "senotypes": senotypes,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "order": order,
        },
    }, 200


@senotypes_bp.route("/senotypes/<string:uuid>", methods=["GET"])
@require_any_senotype_group(ALL_SENOTYPE_GROUPS)
def get_senotype(uuid: str):
    # Check if senotype exists
    senotype = find_senotype(uuid)
    if senotype is None:
        return {"message": "Senotype not found"}, 404

    return {"senotype": senotype}, 200


@senotypes_bp.route("/senotypes", methods=["POST"])
@require_any_senotype_group(ALL_SENOTYPE_GROUPS)
@validate_body(SenotypeRequest)
def create_senotype(body: SenotypeRequest, token_info: TokenInfo):
    # Validate in two steps:
    # 1. Validate general structure using validate_body decorator
    # 2. Perform requests against database and APIs to check values
    try:
        res, err = validate_senotype_request(body, token_info)
        if err:
            return {"message": "Validation error", "errors": err}, 400
    except Exception as e:
        current_app.logger.error(f"Unexpected error during senotype creation validation: {e}")
        return {"message": "An unexpected error occurred during validation"}, 500

    # Create a new UUID for the senotype
    try:
        uuid_res = get_uuid_api_service().create_uuid(
            {"entity_type": "REFERENCE"},
            token_info.token.get_secret_value(),
        )
        uuid_item = uuid_res[0]
    except Exception as e:
        current_app.logger.error(f"Error creating UUID for new senotype: {e}")
        return {"message": "Failed to create UUID for new senotype"}, 500

    # Insert the new senotype into the database
    try:
        now = datetime.now(timezone.utc)
        doc = {
            "uuid": uuid_item["uuid"],
            "sennet_id": uuid_item["sennet_id"],
            "created_by_user_displayname": token_info.name,
            "created_by_user_email": token_info.email,
            "created_by_user_sub": token_info.sub,
            "created_timestamp": now,
            "last_modified_user_displayname": token_info.name,
            "last_modified_user_email": token_info.email,
            "last_modified_user_sub": token_info.sub,
            "last_modified_timestamp": now,
            **res,
        }
        new_doc = insert_senotype(doc)
        if new_doc is None:
            raise Exception("Database insertion failed, no document returned")
    except Exception as e:
        current_app.logger.error(f"Error inserting new senotype into database: {e}")
        return {"message": "Failed to insert new senotype into database"}, 500

    # Reindex the new senotype in the search API
    try:
        get_search_api_service().reindex_senotype(
            new_doc["uuid"],
            token=token_info.token.get_secret_value(),
        )
    except Exception as e:
        current_app.logger.error(
            f"Error reindexing new senotype {new_doc['uuid']} in search API: {e}"
        )

    # Check if user wants the created senotype returned
    return_dict = request.args.get("return_dict", "true")
    if return_dict.lower() == "false":
        return {"message": "Senotype created"}, 201

    return {"senotype": new_doc}, 201


@senotypes_bp.route("/senotypes/<string:uuid>", methods=["PUT"])
@require_any_senotype_group([SenotypeGroup.CURATE, SenotypeGroup.EDIT])
@validate_body(SenotypeRequest)
def update_senotype(
    uuid: str, body: SenotypeRequest, token_info: TokenInfo, user_groups: list[SenotypeGroup]
):
    # Check if senotype exists
    senotype = find_senotype(uuid)
    if senotype is None:
        return {"message": "Senotype not found"}, 404

    # Check if user owns the senotype or is in curate group
    is_curator = SenotypeGroup.CURATE in user_groups
    is_owner = senotype["created_by_user_sub"] == token_info.sub
    if not is_curator and not is_owner:
        return {"message": "You do not have permission to update this senotype"}, 403

    # Validate in two steps:
    # 1. Validate general structure using validate_body decorator
    # 2. Perform requests against database and APIs to check values
    try:
        res, err = validate_senotype_request(body, token_info)
        if err:
            return {"message": "Validation error", "errors": err}, 400
    except Exception as e:
        current_app.logger.error(f"Unexpected error during senotype creation validation: {e}")
        return {"message": "An unexpected error occurred during validation"}, 500

    # Update the senotype in the database
    try:
        doc = {
            "uuid": senotype["uuid"],
            "sennet_id": senotype["sennet_id"],
            "created_by_user_displayname": senotype["created_by_user_displayname"],
            "created_by_user_email": senotype["created_by_user_email"],
            "created_by_user_sub": senotype["created_by_user_sub"],
            "created_timestamp": senotype["created_timestamp"],
            "last_modified_user_displayname": senotype["last_modified_user_displayname"],
            "last_modified_user_email": senotype["last_modified_user_email"],
            "last_modified_user_sub": senotype["last_modified_user_sub"],
            "last_modified_timestamp": datetime.now(timezone.utc),
            **res,
        }
        new_doc = update_db_senotype(uuid, doc)
        if new_doc is None:
            raise Exception("Database update failed, no document returned")
    except Exception as e:
        current_app.logger.error(f"Error updating senotype in database: {e}")
        return {"message": "Failed to update senotype in database"}, 500

    # Reindex the updated senotype in the search API
    try:
        get_search_api_service().reindex_senotype(
            new_doc["uuid"],
            token=token_info.token.get_secret_value(),
        )
    except Exception as e:
        current_app.logger.error(
            f"Error reindexing updated senotype {new_doc['uuid']} in search API: {e}"
        )

    # Check if user wants the updated senotype returned
    return_dict = request.args.get("return_dict", "true")
    if return_dict.lower() == "false":
        return {"message": "Senotype updated"}, 200

    return {"senotype": new_doc}, 200


@senotypes_bp.route("/senotypes/<string:uuid>", methods=["DELETE"])
@require_any_senotype_group([SenotypeGroup.CURATE, SenotypeGroup.EDIT])
def delete_senotype(uuid: str, token_info: TokenInfo, user_groups: list[SenotypeGroup]):
    # Check if senotype exists
    senotype = find_senotype(uuid)
    if senotype is None:
        return {"message": "Senotype not found"}, 404

    # Check if user owns the senotype or is in curate group
    is_curator = SenotypeGroup.CURATE in user_groups
    is_owner = senotype["created_by_user_sub"] == token_info.sub
    if not is_curator and not is_owner:
        return {"message": "You do not have permission to delete this senotype"}, 403

    # Delete the senotype from the database
    result = delete_db_senotype(uuid)
    if not result:
        return {"message": "Senotype not found"}, 404

    return {"message": "Senotype deleted"}, 200
