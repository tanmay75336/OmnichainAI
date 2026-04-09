from flask import jsonify


def success_response(message, data=None, status_code=200):
    return jsonify({"success": True, "message": message, "data": data or {}}), status_code
