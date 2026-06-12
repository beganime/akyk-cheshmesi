import logging

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        return response

    request = context.get("request")
    view = context.get("view")
    logger.exception(
        "Unhandled API exception | path=%s view=%s",
        getattr(request, "path", ""),
        view.__class__.__name__ if view else "",
    )

    detail = str(exc) if getattr(settings, "DEBUG", False) else "Internal server error"
    return Response({"detail": detail}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
