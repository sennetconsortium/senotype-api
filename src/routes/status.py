from flask import Blueprint

status_bp = Blueprint("status", __name__)


@status_bp.route("/", methods=["GET"])
def get_status():
    return {"status": "ok"}, 200
