"""URL routes for netbox_barcode_plugin."""

from django.urls import path

from . import views

app_name = "netbox_barcode_plugin"

urlpatterns = [
    path("", views.ScanView.as_view(), name="scan"),
    path("api/lookup/", views.lookup, name="api_lookup"),
    path(
        "api/cables/<int:cable_id>/status/",
        views.update_cable_status,
        name="api_cable_status_update",
    ),
]
