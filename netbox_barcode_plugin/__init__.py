"""NetBox Barcode Plugin."""

try:
    from netbox.plugins import PluginConfig
except ModuleNotFoundError:  # pragma: no cover - used only outside NetBox
    class PluginConfig:  # type: ignore[no-redef]
        """Minimal fallback so local tests can be collected without NetBox."""

        pass


class NetBoxBarcodePluginConfig(PluginConfig):
    """NetBox plugin configuration."""

    name = "netbox_barcode_plugin"
    verbose_name = "NetBox Barcode Plugin"
    description = "Scan barcodes to look up cables, display traces, and update cable status."
    version = "0.1.0"
    base_url = "barcode"
    min_version = "4.6.0"
    max_version = "4.6.99"


config = NetBoxBarcodePluginConfig
