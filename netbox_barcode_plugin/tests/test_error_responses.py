import json

import pytest


def test_error_response_common_shape():
    pytest.importorskip("django")
    from netbox_barcode_plugin.exceptions import error_response

    response = error_response("エラー", "machine_code", status=400)
    payload = json.loads(response.content.decode())

    assert response.status_code == 400
    assert payload == {
        "success": False,
        "error": "エラー",
        "code": "machine_code",
    }


def test_api_get_method_returns_json_405():
    pytest.importorskip("django")
    from django.test import RequestFactory
    from netbox_barcode_plugin.views import json_post_required

    def dummy(request):
        raise AssertionError("should not run")

    request = RequestFactory().get("/plugins/barcode/api/lookup/")
    response = json_post_required(dummy)(request)
    payload = json.loads(response.content.decode())

    assert response.status_code == 405
    assert payload["success"] is False
    assert payload["code"] == "method_not_allowed"


def test_invalid_json_parse_error():
    pytest.importorskip("django")
    from django.test import RequestFactory
    from netbox_barcode_plugin.constants import CODE_INVALID_JSON
    from netbox_barcode_plugin.exceptions import BarcodePluginError
    from netbox_barcode_plugin.utils import parse_json_request

    request = RequestFactory().post(
        "/plugins/barcode/api/lookup/",
        data="{not json",
        content_type="application/json",
    )

    with pytest.raises(BarcodePluginError) as exc:
        parse_json_request(request)

    assert exc.value.status == 400
    assert exc.value.code == CODE_INVALID_JSON
