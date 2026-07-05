"""NetBox-facing service layer for Cable lookup, trace, and updates."""

from contextlib import contextmanager

from django.db.models import Q

from .constants import (
    CF_BARCODE,
    CF_CABLE_STATUS,
    CODE_CABLE_NOT_FOUND,
    CODE_CUSTOM_FIELD_NOT_CONFIGURED,
    CODE_INVALID_STATUS,
    CODE_MULTIPLE_CABLES_FOUND,
    CODE_PERMISSION_DENIED,
    DEFAULT_CABLE_STATUS,
    REQUIRED_LOOKUP_CUSTOM_FIELDS,
    REQUIRED_UPDATE_CUSTOM_FIELDS,
    VALID_CABLE_STATUSES,
)
from .exceptions import BarcodePluginError
from .permissions import can_change_cable, can_view_cable
from .utils import (
    cable_status_to_dict,
    cable_status_value_label,
    get_object_url,
    object_ref,
    status_options,
)


def get_cable_model():
    """Import and return NetBox's Cable model lazily."""

    from dcim.models import Cable

    return Cable


def get_custom_field_model():
    """Import and return NetBox's CustomField model lazily."""

    from extras.models import CustomField

    return CustomField


def _get_cable_content_type():
    """Return the ContentType for dcim.Cable."""

    from django.contrib.contenttypes.models import ContentType

    return ContentType.objects.get_for_model(get_cable_model())


def _custom_field_applies_to_cable(custom_field):
    """Best-effort check that a CustomField is configured for Cable.

    NetBox 4.x associates custom fields to content types. Attribute names have
    changed over NetBox versions, so this helper tolerates both common relation
    names and falls back to True when a relation is not introspectable.
    """

    cable_ct = _get_cable_content_type()

    for attr in ("object_types", "content_types"):
        relation = getattr(custom_field, attr, None)
        if relation is None:
            continue
        try:
            return relation.filter(pk=cable_ct.pk).exists()
        except Exception:
            continue

    # Older/alternate implementations may expose a CSV/model string. If none is
    # available, existence by name is the safest deploy-time check.
    return True


def ensure_custom_fields(required_names=REQUIRED_LOOKUP_CUSTOM_FIELDS):
    """Ensure required Cable custom fields exist.

    Raises a JSON-ready ``BarcodePluginError`` instead of causing a 500 stack
    trace when NetBox has not been configured yet.
    """

    CustomField = get_custom_field_model()

    for name in required_names:
        matches = CustomField.objects.filter(name=name)
        configured = False
        for custom_field in matches:
            if _custom_field_applies_to_cable(custom_field):
                configured = True
                break
        if not configured:
            raise BarcodePluginError(
                f"必須カスタムフィールド '{name}' が設定されていません。",
                CODE_CUSTOM_FIELD_NOT_CONFIGURED,
                status=500,
            )


def _safe_cf_value(obj, name):
    """Return a custom field value from an object without raising KeyError."""

    return (getattr(obj, "custom_field_data", None) or {}).get(name)


def find_cable_by_barcode(normalized_code):
    """Find one Cable by label or custom field barcode.

    Search rules:
    - Cable.label: case-insensitive exact match
    - custom_field_data["barcode"]: case-insensitive exact match
    - no partial matches
    - no stripping of ``CBL-``; *normalized_code* is used whole
    - same Cable matching both fields counts as one result
    - different matching Cables produce 409
    """

    Cable = get_cable_model()

    # The OR query narrows candidates efficiently, then Python verifies exact
    # case-insensitive equality and builds matched_by while deduplicating.
    candidates = Cable.objects.filter(
        Q(label__iexact=normalized_code)
        | Q(custom_field_data__barcode__iexact=normalized_code)
    )

    normalized_lower = normalized_code.lower()
    matches_by_pk = {}
    for cable in candidates:
        matched_by = set()
        label = getattr(cable, "label", None)
        if isinstance(label, str) and label.lower() == normalized_lower:
            matched_by.add("label")

        barcode = _safe_cf_value(cable, CF_BARCODE)
        if isinstance(barcode, str) and barcode.lower() == normalized_lower:
            matched_by.add("barcode")

        if matched_by:
            pk = cable.pk
            if pk not in matches_by_pk:
                matches_by_pk[pk] = {"cable": cable, "matched_by": set()}
            matches_by_pk[pk]["matched_by"].update(matched_by)

    if not matches_by_pk:
        raise BarcodePluginError(
            "対象のケーブルが見つかりません。",
            CODE_CABLE_NOT_FOUND,
            status=404,
        )

    if len(matches_by_pk) > 1:
        raise BarcodePluginError(
            "複数のケーブルが一致しました。バーコードまたはラベルの重複を確認してください。",
            CODE_MULTIPLE_CABLES_FOUND,
            status=409,
            extra={"matches_count": len(matches_by_pk)},
        )

    result = next(iter(matches_by_pk.values()))
    order = {"label": 0, "barcode": 1}
    return result["cable"], sorted(result["matched_by"], key=order.get)


def serialize_cable(cable):
    """Serialize a Cable to the API CableObject shape."""

    cf_data = getattr(cable, "custom_field_data", None) or {}
    label = getattr(cable, "label", None)
    display = getattr(cable, "display", None) or label or str(cable)
    return {
        "id": cable.pk,
        "label": label,
        "display": str(display),
        "url": get_object_url(cable),
        "barcode": cf_data.get(CF_BARCODE),
        "status": cable_status_to_dict(cf_data.get(CF_CABLE_STATUS)),
    }


def _iter_relation(obj, attr_name):
    """Safely iterate a Django relation or list attribute."""

    relation = getattr(obj, attr_name, None)
    if relation is None:
        return []
    if hasattr(relation, "all"):
        try:
            return list(relation.all())
        except Exception:
            return []
    try:
        return list(relation)
    except TypeError:
        return [relation]


def _cable_terminations(cable, side):
    """Return Cable terminations for side ``a`` or ``b`` across NetBox APIs."""

    candidates = (
        f"{side}_terminations",
        f"termination_{side}s",
        f"{side}_termination",
        f"termination_{side}",
    )
    terminations = []
    for attr in candidates:
        for item in _iter_relation(cable, attr):
            if item is not None:
                terminations.append(item)
        if terminations:
            break
    return terminations


def _flatten_trace_item(item):
    """Yield likely NetBox objects from a trace item.

    NetBox trace APIs commonly return a list of tuples containing terminations
    and cables. This intentionally skips booleans/None and recursively flattens
    nested lists/tuples so both old and new NetBox versions serialize cleanly.
    """

    if item is None or isinstance(item, (bool, int, float, str)):
        return
    if isinstance(item, (list, tuple, set)):
        for value in item:
            yield from _flatten_trace_item(value)
        return
    yield item


def _trace_from_termination(termination):
    """Run trace() on one cable termination and serialize the path."""

    trace_method = getattr(termination, "trace", None)
    if not callable(trace_method):
        return []

    try:
        raw_trace = trace_method()
    except Exception:
        return []

    refs = []
    seen = set()
    for raw_item in raw_trace or []:
        for obj in _flatten_trace_item(raw_item):
            key = (obj.__class__, getattr(obj, "pk", id(obj)))
            if key in seen:
                continue
            seen.add(key)
            refs.append(object_ref(obj))

    return refs


def _find_cable_index(refs, cable_url):
    """Return the index of *this* cable node within a serialized trace path."""

    if not cable_url:
        return None

    for index, ref in enumerate(refs):
        if ref and ref.get("type") == "cable" and ref.get("url") == cable_url:
            return index
    return None


def _split_full_path(refs, cable_url, origin_side):
    """Split a full end-to-end trace path at *this* cable into A/B sides.

    ``refs`` is a complete path produced by ``trace()`` from one of this
    cable's terminations, so it starts at ``origin_side``'s device and ends at
    the opposite side's device. Splitting at this cable yields the two physical
    sides, each ordered from the cable *outward* to its ultimate endpoint (so
    ``[-1]`` is that side's final connection).

    Returns ``(a_side, b_side)`` or ``None`` when this cable is not present in
    the path (older/edge NetBox behaviors).
    """

    index = _find_cable_index(refs, cable_url)
    if index is None:
        return None

    origin_side_refs = list(reversed(refs[:index]))  # ends at origin device
    far_side_refs = refs[index + 1:]                 # ends at far device

    if origin_side == "a":
        return origin_side_refs, far_side_refs
    return far_side_refs, origin_side_refs


def _physical_endpoint(cable, side):
    """Return the ObjectRef for a cable's directly-connected port on ``side``.

    This is the *physical* port the cable is plugged into on that side (its own
    A/B termination), as opposed to the logical far endpoint reached through
    patch panels by ``trace()``. Returns ``None`` when the side is unconnected.
    """

    for termination in _cable_terminations(cable, side):
        if termination is not None:
            return object_ref(termination)
    return None


def trace_cable(cable):
    """Return A/B side trace arrays and endpoints for a Cable.

    NetBox's ``trace()`` returns the *full* end-to-end path, not a single side.
    Tracing from the A termination therefore starts at the A-side device and
    ends at the B-side device (and vice versa). To report each physical side
    correctly, the full path is split at this cable so that ``a_side`` always
    ends at the A-side endpoint and ``b_side`` at the B-side endpoint.

    Two kinds of endpoints are returned:

    - ``endpoints``: the *physical* ports the cable is directly plugged into on
      each side (this cable's own A/B terminations).
    - ``trace_endpoints``: the *logical* far endpoints reached by following the
      full trace path through patch panels etc. (the last node of each side).
    """

    cable_url = get_object_url(cable)

    a_refs = []
    for termination in _cable_terminations(cable, "a"):
        a_refs.extend(_trace_from_termination(termination))

    split = _split_full_path(a_refs, cable_url, "a") if a_refs else None

    if split is None:
        # The A-side trace did not contain this cable (unconnected A end or an
        # older NetBox). Try tracing from the B termination and splitting that.
        b_refs = []
        for termination in _cable_terminations(cable, "b"):
            b_refs.extend(_trace_from_termination(termination))

        split = _split_full_path(b_refs, cable_url, "b") if b_refs else None

        if split is None:
            # Final fallback: use Cable.trace() when available, otherwise keep
            # whatever partial per-side traces we gathered.
            if not a_refs and not b_refs:
                trace_method = getattr(cable, "trace", None)
                if callable(trace_method):
                    try:
                        raw = trace_method()
                        if isinstance(raw, dict):
                            a_refs = [object_ref(obj) for obj in raw.get("a_side", []) if obj is not None]
                            b_refs = [object_ref(obj) for obj in raw.get("b_side", []) if obj is not None]
                    except Exception:
                        pass
            split = (a_refs, b_refs)

    a_side, b_side = split

    trace = {
        "a_side": a_side,
        "b_side": b_side,
    }
    endpoints = {
        "a_side": _physical_endpoint(cable, "a"),
        "b_side": _physical_endpoint(cable, "b"),
    }
    trace_endpoints = {
        "a_side": a_side[-1] if a_side else None,
        "b_side": b_side[-1] if b_side else None,
    }
    return trace, endpoints, trace_endpoints


def build_lookup_response(user, raw_code, normalized_code, prefix):
    """Build the complete successful lookup response for a CBL barcode."""

    ensure_custom_fields(REQUIRED_LOOKUP_CUSTOM_FIELDS)
    cable, matched_by = find_cable_by_barcode(normalized_code)

    if not can_view_cable(user, cable):
        raise BarcodePluginError(
            "このケーブルを閲覧する権限がありません。",
            CODE_PERMISSION_DENIED,
            status=403,
        )

    trace, endpoints, trace_endpoints = trace_cable(cable)
    return {
        "success": True,
        "type": "cable",
        "input": {
            "code": raw_code,
            "normalized_code": normalized_code,
            "prefix": prefix,
        },
        "cable": serialize_cable(cable),
        "matched_by": matched_by,
        "can_update": can_change_cable(user, cable),
        "status_options": status_options(),
        "trace": trace,
        "endpoints": endpoints,
        "trace_endpoints": trace_endpoints,
        "warnings": [],
    }


def get_cable_or_404(cable_id):
    """Fetch a Cable or raise the API 404 error."""

    Cable = get_cable_model()
    try:
        return Cable.objects.get(pk=cable_id)
    except Cable.DoesNotExist:
        raise BarcodePluginError(
            "対象のケーブルが見つかりません。",
            CODE_CABLE_NOT_FOUND,
            status=404,
        )


def validate_cable_status(value):
    """Validate status update input and return the valid value."""

    if value not in VALID_CABLE_STATUSES:
        raise BarcodePluginError(
            "不正なケーブルステータスです。",
            CODE_INVALID_STATUS,
            status=400,
            extra={"allowed_values": list(VALID_CABLE_STATUSES)},
        )
    return value


@contextmanager
def change_logging_context(request):
    """Wrap saves in NetBox's change_logging context manager.

    The prompt requires NetBox's ``change_logging`` context manager. NetBox 4.6
    records changes via request processors/event tracking, so this helper first
    tries the historical ``change_logging`` import and then falls back to the
    NetBox 4.6 request processor context.
    """

    try:
        from extras.context_managers import change_logging
    except Exception:
        change_logging = None

    if change_logging is not None:
        with change_logging(request):
            yield
        return

    try:
        from utilities.request import apply_request_processors
    except Exception:
        apply_request_processors = None

    if apply_request_processors is not None:
        with apply_request_processors(request):
            yield
        return

    try:
        from netbox.context_managers import event_tracking
    except Exception:  # pragma: no cover - only exercised outside NetBox
        yield
        return

    with event_tracking(request):
        yield


def update_cable_status_value(user, request, cable_id, new_status):
    """Update only ``custom_field_data['cable_status']`` for a Cable."""

    ensure_custom_fields(REQUIRED_UPDATE_CUSTOM_FIELDS)
    new_status = validate_cable_status(new_status)
    cable = get_cable_or_404(cable_id)

    if not can_change_cable(user, cable):
        raise BarcodePluginError(
            "このケーブルを更新する権限がありません。",
            CODE_PERMISSION_DENIED,
            status=403,
        )

    cf_data = dict(getattr(cable, "custom_field_data", None) or {})
    old_status = cf_data.get(CF_CABLE_STATUS) or DEFAULT_CABLE_STATUS

    cf_data[CF_CABLE_STATUS] = new_status
    cable.custom_field_data = cf_data

    # NetBox validates custom fields in full_clean(). The request context is
    # required for ObjectChange generation.
    if hasattr(cable, "full_clean"):
        cable.full_clean()

    with change_logging_context(request):
        cable.save()

    return {
        "success": True,
        "message": "更新しました。",
        "cable": serialize_cable(cable),
        "updated": {
            "field": CF_CABLE_STATUS,
            "old": cable_status_value_label(old_status),
            "new": cable_status_value_label(new_status),
        },
        "can_update": can_change_cable(user, cable),
    }
