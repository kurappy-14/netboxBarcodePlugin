import pytest


def test_barcode_normalization_strips_whitespace():
    pytest.importorskip("django")
    from netbox_barcode_plugin.utils import normalize_barcode

    assert normalize_barcode("  CBL-000001  ") == "CBL-000001"


@pytest.mark.parametrize("value", ["", "   "])
def test_empty_barcode_is_invalid(value):
    pytest.importorskip("django")
    from netbox_barcode_plugin.constants import CODE_INVALID_BARCODE
    from netbox_barcode_plugin.exceptions import BarcodePluginError
    from netbox_barcode_plugin.utils import normalize_barcode

    with pytest.raises(BarcodePluginError) as exc:
        normalize_barcode(value)

    assert exc.value.status == 400
    assert exc.value.code == CODE_INVALID_BARCODE


def test_missing_code_is_invalid():
    pytest.importorskip("django")
    from netbox_barcode_plugin.constants import CODE_MISSING_CODE
    from netbox_barcode_plugin.exceptions import BarcodePluginError
    from netbox_barcode_plugin.utils import normalize_barcode

    with pytest.raises(BarcodePluginError) as exc:
        normalize_barcode(None)

    assert exc.value.code == CODE_MISSING_CODE


def test_non_string_code_is_invalid():
    pytest.importorskip("django")
    from netbox_barcode_plugin.constants import CODE_INVALID_BARCODE
    from netbox_barcode_plugin.exceptions import BarcodePluginError
    from netbox_barcode_plugin.utils import normalize_barcode

    with pytest.raises(BarcodePluginError) as exc:
        normalize_barcode(123)

    assert exc.value.code == CODE_INVALID_BARCODE


def test_129_character_barcode_is_too_long():
    pytest.importorskip("django")
    from netbox_barcode_plugin.constants import CODE_BARCODE_TOO_LONG
    from netbox_barcode_plugin.exceptions import BarcodePluginError
    from netbox_barcode_plugin.utils import normalize_barcode

    with pytest.raises(BarcodePluginError) as exc:
        normalize_barcode("A" * 129)

    assert exc.value.status == 400
    assert exc.value.code == CODE_BARCODE_TOO_LONG


def test_128_character_barcode_is_length_valid():
    pytest.importorskip("django")
    from netbox_barcode_plugin.utils import normalize_barcode

    value = "A" * 128
    assert normalize_barcode(value) == value


def test_prefix_dispatch_supports_cbl_case_insensitive():
    pytest.importorskip("django")
    from netbox_barcode_plugin.utils import get_prefix

    assert get_prefix("cbl-000001") == "CBL"


def test_unsupported_prefix_is_invalid():
    pytest.importorskip("django")
    from netbox_barcode_plugin.constants import CODE_INVALID_PREFIX
    from netbox_barcode_plugin.exceptions import BarcodePluginError
    from netbox_barcode_plugin.utils import get_prefix

    with pytest.raises(BarcodePluginError) as exc:
        get_prefix("DEV-000001")

    assert exc.value.status == 400
    assert exc.value.code == CODE_INVALID_PREFIX


def test_status_options_are_fixed_three_values():
    pytest.importorskip("django")
    from netbox_barcode_plugin.utils import status_options

    assert status_options() == [
        {"value": "not_created", "label": "未作成"},
        {"value": "configured", "label": "作成済み"},
        {"value": "laid", "label": "敷設済み"},
    ]


def test_missing_cable_status_defaults_without_save_side_effect():
    pytest.importorskip("django")
    from netbox_barcode_plugin.utils import cable_status_to_dict

    assert cable_status_to_dict(None) == {
        "value": "not_created",
        "label": "未作成",
        "is_defaulted": True,
    }
