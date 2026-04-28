import atexit
import logging
import os

from flask import Flask
from globus_sdk import ConfidentialAppAuthClient
from pymongo import MongoClient

from common.config import AppConfig
from routes.senotypes import senotypes_bp
from routes.status import status_bp

logging.basicConfig(
    format="[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)


def configure_logger(app: Flask):
    level_name = app.config.get("LOG_LEVEL", "INFO")
    level = getattr(logging, level_name.upper(), logging.INFO)

    fmt = "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.setLevel(level)
    app.logger.addHandler(console)

    app.logger.setLevel(level)


def configure_services(app: Flask, config: AppConfig):
    app.extensions["app_config"] = config

    app.extensions["auth_client"] = ConfidentialAppAuthClient(
        client_id=config.GLOBUS_APP_CLIENT_ID,
        client_secret=config.GLOBUS_APP_CLIENT_SECRET.get_secret_value(),
    )

    mongo_client = MongoClient(
        host=config.MONGO_HOST,
        port=27017,
        username=config.MONGO_USERNAME,
        password=config.MONGO_PASSWORD.get_secret_value(),
        authSource=config.MONGO_DB_NAME,
    )
    app.extensions["mongo_db"] = mongo_client[config.MONGO_DB_NAME]
    atexit.register(mongo_client.close)


def configure_routes(app: Flask):
    app.register_blueprint(senotypes_bp, url_prefix="/senotypes")
    app.register_blueprint(status_bp, url_prefix="/status")


def create_app() -> Flask:
    app = Flask(
        __name__,
        instance_path=os.path.abspath(os.path.join(os.path.dirname(__file__), "instance")),
        instance_relative_config=True,
    )
    app.config.from_pyfile("app.cfg")
    config = AppConfig.model_validate(dict(app.config))
    configure_logger(app)
    configure_services(app, config)
    configure_routes(app)

    return app


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=5010,
        help="Port to run the Flask app on (default: 5010)",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Run the Flask app in debug mode",
    )
    args = parser.parse_args()

    app = create_app()
    app.run(host="0.0.0.0", port=args.port, debug=args.debug, use_reloader=False)
