import functools
import inspect
from enum import Enum
from typing import Type

from flask import request
from pydantic import BaseModel, SecretStr, ValidationError
from requests import HTTPError

from common.context import get_ingest_api_service


class TokenInfo(BaseModel):
    email: str
    name: str
    sub: str
    username: str
    token: SecretStr


class SenotypeGroup(str, Enum):
    CURATE = "senotype_curate"
    EDIT = "senotype_edit"
    PUBLISH = "senotype_publish"


ALL_SENOTYPE_GROUPS: list[SenotypeGroup] = list(SenotypeGroup)


def require_any_senotype_group(groups: SenotypeGroup | list[SenotypeGroup]):
    """
    Decorator that restricts a route to users belonging to at least one of the specified senotype
    groups.

    Validates the bearer token from the Authorization header against the Ingest API and checks the
    user's group membership. If the decorated function accepts ``token_info``, it is populated with
    the authenticated user's details. If it accepts ``senotype_groups``, it is populated with the
    list of senotype groups the user belongs to (i.e. CURATE, EDIT, PUBLISH).

    Parameters
    ----------
    groups : SenotypeGroup or list[SenotypeGroup]
        One or more groups that the user must belong to in order to access the route.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            auth = request.authorization
            if not auth or auth.type != "bearer":
                return {"message": "Missing or invalid Authorization header"}, 401

            token = auth.token
            if not token:
                return {"message": "Missing token"}, 401

            required_groups = [groups] if isinstance(groups, SenotypeGroup) else list(groups)

            ingest_service = get_ingest_api_service()

            try:
                privs = ingest_service.get_senotype_privs(token)
            except HTTPError as e:
                if e.response is not None and e.response.status_code == 401:
                    return {"message": "Invalid or expired token"}, 401
                return {"message": "Failed to retrieve senotype privileges"}, 500

            user_groups = [g for g in SenotypeGroup if privs.get(f"has_{g.value}", False)]

            has_access = any(g in user_groups for g in required_groups)
            if not has_access:
                groups_str = ", ".join(g.value for g in required_groups)
                return {
                    "message": f"User does not have senotype group membership: {groups_str}"
                }, 403

            sig = inspect.signature(func)

            if "token_info" in sig.parameters:
                try:
                    token_data = ingest_service.get_token_info(token)
                except HTTPError:
                    return {"message": "Failed to validate token"}, 401

                kwargs["token_info"] = TokenInfo(
                    email=token_data["email"],
                    name=token_data["name"],
                    sub=token_data["sub"],
                    username=token_data["username"],
                    token=SecretStr(token),
                )

            if "user_groups" in sig.parameters:
                kwargs["user_groups"] = user_groups

            return func(*args, **kwargs)

        return wrapper

    return decorator


def validate_body(model: Type[BaseModel]):
    """
    Decorator that parses and validates the JSON request body against a Pydantic model.

    Requires the request ``Content-Type`` to be ``application/json``. If validation succeeds and
    the decorated function accepts a ``body`` parameter, the parsed model instance is passed as that
    argument.

    Parameters
    ----------
    model : Type[BaseModel]
        The Pydantic model class used to validate the request body.
    """

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
                kwargs["body"] = parsed

            return func(*args, **kwargs)

        return wrapper

    return decorator
