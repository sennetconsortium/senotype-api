import functools
import inspect
from typing import Type

from flask import request
from globus_sdk import AccessTokenAuthorizer, GroupsClient
from pydantic import BaseModel, SecretStr, ValidationError

from common.context import get_auth_client, get_globus_group_uuids


class TokenInfo(BaseModel):
    email: str
    groups: list[str] = []
    name: str
    sub: str
    username: str
    token: SecretStr


GLOBUS_GROUPS_RESOURCE_SERVER = "groups.api.globus.org"


def require_globus_groups_token(required_group_name: str | None = None):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            auth = request.authorization
            if not auth or auth.type != "bearer":
                return {"message": "Missing or invalid Authorization header"}, 401

            token = auth.token
            if not token or auth.type != "bearer":
                return {"message": "Missing token"}, 401

            introspect = get_auth_client().oauth2_token_introspect(token)

            if not introspect.get("active"):
                return {"message": "Invalid or expired token"}, 401

            audiences = introspect.get("aud", [])
            if GLOBUS_GROUPS_RESOURCE_SERVER not in audiences:
                return {"message": "Token is not valid for Globus Groups"}, 403

            groups_client = GroupsClient(authorizer=AccessTokenAuthorizer(token))
            groups = [g["id"] for g in groups_client.get_my_groups()]

            token_info = TokenInfo(
                email=introspect["email"],
                name=introspect["name"],
                groups=groups,
                sub=introspect["sub"],
                username=introspect["username"],
                token=SecretStr(token),
            )

            # If a required group name is specified, check membership
            if required_group_name:
                globus_group_uuids = get_globus_group_uuids()
                required_group_uuid = globus_group_uuids.get(required_group_name)
                if not required_group_uuid:
                    return {
                        "message": f"Required group '{required_group_name}' is not configured"
                    }, 500

                if str(required_group_uuid) not in groups:
                    return {
                        "message": f"User is not a member of required group: {required_group_name}"
                    }, 403

            sig = inspect.signature(func)
            if "token_info" in sig.parameters:
                return func(*args, token_info=token_info, **kwargs)
            else:
                return func(*args, **kwargs)

        return wrapper

    return decorator


def validate_body(model: Type[BaseModel]):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not request.is_json:
                return {"message": "Content-Type must be application/json"}, 415

            try:
                parsed = model.model_validate(request.get_json())
            except ValidationError as e:
                errors = {}
                for err in e.errors():
                    field = str(err["loc"][0]) if err["loc"] else "body"
                    msg = err["msg"]
                    msg = msg.removeprefix("Value error, ")
                    errors.setdefault(field, []).append(msg)
                return {"message": "Validation error", "errors": errors}, 400

            sig = inspect.signature(func)
            if "body" in sig.parameters:
                return func(*args, body=parsed, **kwargs)
            else:
                return func(*args, **kwargs)

        return wrapper

    return decorator
