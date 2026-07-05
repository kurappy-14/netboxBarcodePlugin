import pytest


def test_plugin_config_values():
    pytest.importorskip("netbox")

    from netbox_barcode_plugin import NetBoxBarcodePluginConfig

    assert NetBoxBarcodePluginConfig.name == "netbox_barcode_plugin"
    assert NetBoxBarcodePluginConfig.verbose_name == "NetBox Barcode Plugin"
    assert NetBoxBarcodePluginConfig.version == "0.1.0"
    assert NetBoxBarcodePluginConfig.base_url == "barcode"


def test_url_namespace():
    pytest.importorskip("django")

    from netbox_barcode_plugin import urls

    assert urls.app_name == "netbox_barcode_plugin"
    names = {pattern.name for pattern in urls.urlpatterns}
    assert {"scan", "api_lookup", "api_cable_status_update"} <= names
