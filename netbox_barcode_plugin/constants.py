"""Shared constants for netbox_barcode_plugin.

All machine-readable codes are English snake_case. All user-facing labels and
messages are Japanese, per the specification.
"""

# --- Custom field names (DCIM > Cable) ---
CF_BARCODE = "barcode"
CF_CABLE_STATUS = "cable_status"

# Custom fields that must exist for the lookup API.
REQUIRED_LOOKUP_CUSTOM_FIELDS = (CF_BARCODE, CF_CABLE_STATUS)
# Custom fields that must exist for the status update API.
REQUIRED_UPDATE_CUSTOM_FIELDS = (CF_CABLE_STATUS,)

# --- Barcode validation ---
MAX_BARCODE_LENGTH = 128

# --- Prefix dispatch ---
# Maps an uppercase prefix token to a logical object type. New prefixes (e.g.
# ``DEV-`` -> ``device``) can be registered here without touching the view.
PREFIX_CABLE = "CBL"
PREFIX_MAP = {
    PREFIX_CABLE: "cable",
}

# --- Cable status (Selection custom field) ---
STATUS_NOT_CREATED = "not_created"
STATUS_CONFIGURED = "configured"
STATUS_LAID = "laid"

DEFAULT_CABLE_STATUS = STATUS_NOT_CREATED

# Ordered (value, label) pairs used for status_options and label lookups.
CABLE_STATUS_CHOICES = (
    (STATUS_NOT_CREATED, "未作成"),
    (STATUS_CONFIGURED, "作成済み"),
    (STATUS_LAID, "敷設済み"),
)
CABLE_STATUS_LABELS = dict(CABLE_STATUS_CHOICES)
VALID_CABLE_STATUSES = tuple(value for value, _ in CABLE_STATUS_CHOICES)

# --- Error codes (machine readable) ---
CODE_INVALID_JSON = "invalid_json"
CODE_MISSING_CODE = "missing_code"
CODE_INVALID_BARCODE = "invalid_barcode"
CODE_BARCODE_TOO_LONG = "barcode_too_long"
CODE_INVALID_PREFIX = "invalid_prefix"
CODE_CABLE_NOT_FOUND = "cable_not_found"
CODE_MULTIPLE_CABLES_FOUND = "multiple_cables_found"
CODE_PERMISSION_DENIED = "permission_denied"
CODE_INVALID_STATUS = "invalid_status"
CODE_CUSTOM_FIELD_NOT_CONFIGURED = "custom_field_not_configured"
CODE_METHOD_NOT_ALLOWED = "method_not_allowed"
CODE_INTERNAL_ERROR = "internal_error"
