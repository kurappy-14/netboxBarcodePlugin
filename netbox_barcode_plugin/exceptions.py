"""Application exceptions and JSON error helpers."""

from django.http import JsonResponse


class BarcodePluginError(Exception):
    """Base exception for expected API errors."""

    def __init__(self, message, code, status=400, extra=None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status
        self.extra = extra or {}


def error_response(message, code, status=400, **extra):
    """Return the unified JSON error shape required by the API spec."""

    payload = {
        "success": False,
        "error": message,
        "code": code,
    }
    payload.update(extra)
    return JsonResponse(payload, status=status)


def response_from_exception(exc):
    """Convert a :class:`BarcodePluginError` into a JSON response."""

    return error_response(exc.message, exc.code, status=exc.status, **exc.extra)
