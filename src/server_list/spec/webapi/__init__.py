# Web API Package
"""Common utilities for webapi endpoints."""

import flask


def success_response(data):
    """Create a success response.

    Args:
        data: Response data (will be JSON serialized)

    Returns:
        Flask JSON response with {"success": True, "data": data}
    """
    return flask.jsonify({"success": True, "data": data})


def error_response(message: str, status_code: int = 404):
    """Create an error response.

    Args:
        message: Error message
        status_code: HTTP status code (default: 404)

    Returns:
        Flask JSON response with {"success": False, "error": message} and status code
    """
    return flask.jsonify({"success": False, "error": message}), status_code
