from flask import jsonify
from werkzeug.exceptions import HTTPException


class AppError(Exception):
    status_code = 500

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code


class ValidationError(AppError):
    status_code = 400


class ExternalAPIError(AppError):
    status_code = 502


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(error):
        return jsonify({"success": False, "error": error.message}), error.status_code

    @app.errorhandler(ValueError)
    def handle_value_error(error):
        return jsonify({"success": False, "error": str(error)}), 400

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        return (
            jsonify(
                {
                    "success": False,
                    "error": error.description,
                    "status_code": error.code,
                }
            ),
            error.code,
        )

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        app.logger.exception("Unhandled error: %s", error)
        return jsonify(
            {"success": False, "error": "An unexpected server error occurred."}
        ), 500
