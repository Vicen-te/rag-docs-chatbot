"""DRF exception handler that wraps every error in a consistent envelope."""
from __future__ import annotations

from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response
    response.data = {
        "error": {
            "code": getattr(exc, "default_code", "error"),
            "message": str(exc),
            "details": response.data,
        }
    }
    return response
