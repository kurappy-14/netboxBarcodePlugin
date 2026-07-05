"""Views and JSON API endpoints for netbox_barcode_plugin."""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.views.generic import TemplateView

from .constants import (
    CODE_INTERNAL_ERROR,
    CODE_INVALID_STATUS,
    CODE_METHOD_NOT_ALLOWED,
    PREFIX_CABLE,
)
from .exceptions import BarcodePluginError, error_response, response_from_exception
from .services import build_lookup_response, update_cable_status_value
from .utils import get_prefix, normalize_barcode, parse_json_request


class ScanView(LoginRequiredMixin, TemplateView):
    """Render the smartphone barcode scanning page."""

    template_name = "netbox_barcode_plugin/scan.html"


def json_post_required(view_func):
    """Require POST while returning the plugin's JSON error shape."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if request.method != "POST":
            return error_response(
                "許可されていないHTTPメソッドです。",
                CODE_METHOD_NOT_ALLOWED,
                status=405,
            )
        return view_func(request, *args, **kwargs)

    return _wrapped


def _api_exception_response(exc):
    """Convert expected and unexpected exceptions to JSON responses."""

    if isinstance(exc, BarcodePluginError):
        return response_from_exception(exc)

    return error_response(
        "サーバー内部でエラーが発生しました。",
        CODE_INTERNAL_ERROR,
        status=500,
    )


@login_required
@csrf_protect
@json_post_required
def lookup(request):
    """POST /plugins/barcode/api/lookup/."""

    try:
        data = parse_json_request(request)
        raw_code = data.get("code")
        normalized_code = normalize_barcode(raw_code)
        prefix = get_prefix(normalized_code)

        if prefix == PREFIX_CABLE:
            payload = build_lookup_response(
                request.user,
                raw_code,
                normalized_code,
                prefix,
            )
            return JsonResponse(payload)

        # Defensive fallback; get_prefix currently raises before this branch.
        return error_response(
            "未対応のバーコードプレフィックスです。",
            "invalid_prefix",
            status=400,
        )
    except Exception as exc:  # noqa: BLE001 - API must not leak tracebacks
        return _api_exception_response(exc)


@login_required
@csrf_protect
@json_post_required
def update_cable_status(request, cable_id):
    """POST /plugins/barcode/api/cables/<cable_id>/status/."""

    try:
        data = parse_json_request(request)
        if "cable_status" not in data:
            raise BarcodePluginError(
                "ケーブルステータスが指定されていません。",
                CODE_INVALID_STATUS,
                status=400,
                extra={"allowed_values": ["not_created", "configured", "laid"]},
            )

        payload = update_cable_status_value(
            request.user,
            request,
            cable_id,
            data.get("cable_status"),
        )
        return JsonResponse(payload)
    except Exception as exc:  # noqa: BLE001 - API must not leak tracebacks
        return _api_exception_response(exc)
