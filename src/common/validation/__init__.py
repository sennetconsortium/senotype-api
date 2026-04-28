import functools

from flask import current_app


def with_app_context(func):
    app = current_app._get_current_object()  # type: ignore

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with app.app_context():
            return func(*args, **kwargs)

    return wrapper
