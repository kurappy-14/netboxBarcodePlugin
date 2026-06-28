import pytest


class FakeUser:
    def __init__(self, authenticated=True, superuser=False, perms=None):
        self.is_authenticated = authenticated
        self.is_superuser = superuser
        self.perms = set(perms or [])

    def has_perm(self, perm, obj=None):
        return perm in self.perms


def test_view_permission_denied_for_user_without_object_permission():
    pytest.importorskip("django")
    from netbox_barcode_plugin.permissions import can_view_cable

    assert can_view_cable(FakeUser(perms=[]), object()) is False


def test_view_permission_allowed_with_object_permission():
    pytest.importorskip("django")
    from netbox_barcode_plugin.permissions import can_view_cable

    assert can_view_cable(FakeUser(perms=["dcim.view_cable"]), object()) is True


def test_can_update_false_without_change_permission():
    pytest.importorskip("django")
    from netbox_barcode_plugin.permissions import can_change_cable

    assert can_change_cable(FakeUser(perms=["dcim.view_cable"]), object()) is False


def test_can_update_true_with_change_permission():
    pytest.importorskip("django")
    from netbox_barcode_plugin.permissions import can_change_cable

    assert can_change_cable(FakeUser(perms=["dcim.change_cable"]), object()) is True


def test_superuser_can_update():
    pytest.importorskip("django")
    from netbox_barcode_plugin.permissions import can_change_cable

    assert can_change_cable(FakeUser(superuser=True), object()) is True
