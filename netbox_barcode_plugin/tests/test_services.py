from contextlib import contextmanager

import pytest


class FakeCable:
    objects = None

    class DoesNotExist(Exception):
        pass

    def __init__(self, pk, label=None, barcode=None, cable_status=None):
        self.pk = pk
        self.id = pk
        self.label = label
        self.display = label or f"Cable {pk}"
        self.custom_field_data = {}
        if barcode is not None:
            self.custom_field_data["barcode"] = barcode
        if cable_status is not None:
            self.custom_field_data["cable_status"] = cable_status
        self.saved = False
        self.cleaned = False

    def get_absolute_url(self):
        return f"/dcim/cables/{self.pk}/"

    def full_clean(self):
        self.cleaned = True

    def save(self):
        self.saved = True


class FakeManager:
    def __init__(self, items):
        self.items = items

    def filter(self, *args, **kwargs):
        return self.items

    def get(self, pk):
        for item in self.items:
            if item.pk == pk:
                return item
        raise FakeCable.DoesNotExist()


def services_module():
    pytest.importorskip("django")
    return pytest.importorskip("netbox_barcode_plugin.services")


def patch_cables(monkeypatch, cables):
    services = services_module()
    FakeCable.objects = FakeManager(cables)
    monkeypatch.setattr(services, "get_cable_model", lambda: FakeCable)
    return services


def test_find_cable_by_label_case_insensitive(monkeypatch):
    services = patch_cables(monkeypatch, [FakeCable(1, label="CBL-000001")])

    cable, matched_by = services.find_cable_by_barcode("cbl-000001")

    assert cable.pk == 1
    assert matched_by == ["label"]


def test_find_cable_by_barcode_case_insensitive(monkeypatch):
    services = patch_cables(monkeypatch, [FakeCable(2, label="Any", barcode="CBL-000002")])

    cable, matched_by = services.find_cable_by_barcode("cbl-000002")

    assert cable.pk == 2
    assert matched_by == ["barcode"]


def test_same_cable_label_and_barcode_is_one_match(monkeypatch):
    services = patch_cables(monkeypatch, [FakeCable(3, label="CBL-000003", barcode="CBL-000003")])

    cable, matched_by = services.find_cable_by_barcode("CBL-000003")

    assert cable.pk == 3
    assert matched_by == ["label", "barcode"]


def test_multiple_distinct_cables_returns_409(monkeypatch):
    services = patch_cables(
        monkeypatch,
        [
            FakeCable(4, label="CBL-DUP001"),
            FakeCable(5, label="Other", barcode="CBL-DUP001"),
        ],
    )
    from netbox_barcode_plugin.constants import CODE_MULTIPLE_CABLES_FOUND
    from netbox_barcode_plugin.exceptions import BarcodePluginError

    with pytest.raises(BarcodePluginError) as exc:
        services.find_cable_by_barcode("CBL-DUP001")

    assert exc.value.status == 409
    assert exc.value.code == CODE_MULTIPLE_CABLES_FOUND
    assert "matches_count" in exc.value.extra


def test_not_found_returns_404(monkeypatch):
    services = patch_cables(monkeypatch, [FakeCable(1, label="CBL-000001")])
    from netbox_barcode_plugin.constants import CODE_CABLE_NOT_FOUND
    from netbox_barcode_plugin.exceptions import BarcodePluginError

    with pytest.raises(BarcodePluginError) as exc:
        services.find_cable_by_barcode("CBL-NOTFOUND")

    assert exc.value.status == 404
    assert exc.value.code == CODE_CABLE_NOT_FOUND


def test_partial_match_is_not_accepted(monkeypatch):
    services = patch_cables(monkeypatch, [FakeCable(1, label="CBL-000001")])
    from netbox_barcode_plugin.exceptions import BarcodePluginError

    with pytest.raises(BarcodePluginError):
        services.find_cable_by_barcode("CBL-000")


def test_custom_field_missing_returns_500(monkeypatch):
    services = services_module()

    class EmptyManager:
        def filter(self, **kwargs):
            return []

    class FakeCustomField:
        objects = EmptyManager()

    monkeypatch.setattr(services, "get_custom_field_model", lambda: FakeCustomField)

    from netbox_barcode_plugin.constants import CODE_CUSTOM_FIELD_NOT_CONFIGURED
    from netbox_barcode_plugin.exceptions import BarcodePluginError

    with pytest.raises(BarcodePluginError) as exc:
        services.ensure_custom_fields(("barcode",))

    assert exc.value.status == 500
    assert exc.value.code == CODE_CUSTOM_FIELD_NOT_CONFIGURED


def test_update_status_updates_only_cable_status_and_uses_change_logging(monkeypatch):
    services = patch_cables(monkeypatch, [FakeCable(10, label="CBL-10", barcode="CBL-10", cable_status="configured")])
    cable = FakeCable.objects.items[0]
    calls = {"change_logging": 0}

    monkeypatch.setattr(services, "ensure_custom_fields", lambda required_names: None)
    monkeypatch.setattr(services, "can_change_cable", lambda user, obj: True)

    @contextmanager
    def fake_change_logging_context(request):
        calls["change_logging"] += 1
        yield

    monkeypatch.setattr(services, "change_logging_context", fake_change_logging_context)

    payload = services.update_cable_status_value(object(), object(), 10, "laid")

    assert payload["success"] is True
    assert cable.custom_field_data["cable_status"] == "laid"
    assert cable.custom_field_data["barcode"] == "CBL-10"
    assert cable.cleaned is True
    assert cable.saved is True
    assert calls["change_logging"] == 1


def test_invalid_status_returns_400():
    services = services_module()
    from netbox_barcode_plugin.constants import CODE_INVALID_STATUS
    from netbox_barcode_plugin.exceptions import BarcodePluginError

    with pytest.raises(BarcodePluginError) as exc:
        services.validate_cable_status("invalid")

    assert exc.value.status == 400
    assert exc.value.code == CODE_INVALID_STATUS
    assert exc.value.extra["allowed_values"] == ["not_created", "configured", "laid"]
