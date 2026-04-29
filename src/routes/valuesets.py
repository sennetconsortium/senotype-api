from flask import Blueprint, request

from common.database.valuesets import find_valuesets

valuesets_bp = Blueprint("valuesets", __name__)


@valuesets_bp.route("/valuesets", methods=["GET"])
def get_valuesets():
    # get predicate_term from query parameters
    predicate_term = request.args.get("predicate_term")
    valuesets = find_valuesets(predicate_term)
    return {"valuesets": [valueset.model_dump() for valueset in valuesets]}, 200
