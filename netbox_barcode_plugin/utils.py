"""Request parsing, barcode validation, and small serialization helpers."""

import json
from json import JSONDecodeError

from .constants import (
    CABLE_STATUS_CHOICES,
    CABLE_STATUS_LABELS,
    CODE_BARCODE_TOO_LONG,
    CODE_INVALID_BARCODE,
    CODE_INVALID_JSON,
    CODE_INVALID_PREFIX,
    CODE_MISSING_CODE,
    DEFAULT_CABLE_STATUS,
    MAX_BARCODE_LENGTH,
    PREFIX_MAP,
)
from .exceptions import BarcodePluginError


def parse_json_request(request):
    """Parse a JSON request body into a dict.

    The plugin accepts JSON only for its API endpoints. Malformed JSON and
    non-object JSON both become the API's standard ``invalid_json`` response.
    """

    try:
        raw_body = request.body.decode(request.encoding or "utf-8")
        data = json.loads(raw_body or "{}")
    except (UnicodeDecodeError, JSONDecodeError, TypeError):
        raise BarcodePluginError(
            "リクエストJSONを解析できません。",
            CODE_INVALID_JSON,
            status=400,
        )

    if not isinstance(data, dict):
        raise BarcodePluginError(
            "リクエストJSONを解析できません。",
            CODE_INVALID_JSON,
            status=400,
        )
    return data


def normalize_barcode(raw_code):
    """Strip leading/trailing whitespace and validate barcode length/type."""

    if raw_code is None:
        raise BarcodePluginError(
            "バーコード値が指定されていません。",
            CODE_MISSING_CODE,
            status=400,
        )
    if not isinstance(raw_code, str):
        raise BarcodePluginError(
            "バーコード値は文字列で指定してください。",
            CODE_INVALID_BARCODE,
            status=400,
        )

    normalized = raw_code.strip()
    if not normalized:
        raise BarcodePluginError(
            "バーコード値が空です。",
            CODE_INVALID_BARCODE,
            status=400,
        )
    if len(normalized) > MAX_BARCODE_LENGTH:
        raise BarcodePluginError(
            f"バーコード値が長すぎます。{MAX_BARCODE_LENGTH}文字以内で指定してください。",
            CODE_BARCODE_TOO_LONG,
            status=400,
        )

    return normalized


def get_prefix(normalized_code):
    """Return the uppercase prefix token for a normalized barcode.

    Initial implementation supports ``CBL-`` only, but the map is intentionally
    separate so new prefixes can be added without changing the lookup view.
    """

    upper_code = normalized_code.upper()
    for prefix in PREFIX_MAP:
        if upper_code.startswith(f"{prefix}-"):
            return prefix

    raise BarcodePluginError(
        "未対応のバーコードプレフィックスです。",
        CODE_INVALID_PREFIX,
        status=400,
    )


def status_options():
    """Return the fixed UI options for the cable_status custom field."""

    return [{"value": value, "label": label} for value, label in CABLE_STATUS_CHOICES]


def cable_status_to_dict(value):
    """Convert a custom field value to the API CableStatus shape.

    Missing/blank/null values are displayed as ``not_created`` but are not saved
    by lookup operations.
    """

    is_defaulted = value in (None, "")
    status_value = DEFAULT_CABLE_STATUS if is_defaulted else value
    label = CABLE_STATUS_LABELS.get(status_value, str(status_value))
    return {
        "value": status_value,
        "label": label,
        "is_defaulted": is_defaulted,
    }


def cable_status_value_label(value):
    """Return the compact status shape used in update.old/update.new."""

    status = cable_status_to_dict(value)
    return {
        "value": status["value"],
        "label": status["label"],
    }


def object_type_name(obj):
    """Return a stable lowercase object type name for trace JSON."""

    meta = getattr(obj, "_meta", None)
    if meta is not None:
        return getattr(meta, "model_name", obj.__class__.__name__).lower()
    return obj.__class__.__name__.lower()


def get_object_url(obj):
    """Return an object's NetBox detail URL when available."""

    if obj is None:
        return None
    get_absolute_url = getattr(obj, "get_absolute_url", None)
    if callable(get_absolute_url):
        try:
            return get_absolute_url()
        except Exception:
            return None
    return None


def object_display_name(obj):
    """Return a user-friendly display name for an object."""

    if obj is None:
        return ""

    display = getattr(obj, "display", None)
    if display:
        return str(display)

    name = getattr(obj, "name", None)
    if name:
        device = get_object_device_name(obj)
        return f"{device} {name}" if device else str(name)

    label = getattr(obj, "label", None)
    if label:
        return str(label)

    return str(obj)


def get_object_device_name(obj):
    """Best-effort extraction of a related device name for ports/interfaces."""

    device = getattr(obj, "device", None)
    if device is not None:
        return getattr(device, "name", str(device))

    # Some module/interface related models expose a parent object that in turn
    # has a device.
    parent = getattr(obj, "parent", None)
    if parent is not None:
        device = getattr(parent, "device", None)
        if device is not None:
            return getattr(device, "name", str(device))

    return None


def object_ref(obj):
    """Serialize a NetBox object as the API's ObjectRef shape."""

    if obj is None:
        return None
    return {
        "name": object_display_name(obj),
        "type": object_type_name(obj),
        "device": get_object_device_name(obj),
        "url": get_object_url(obj),
    }
