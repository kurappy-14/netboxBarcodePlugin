"""Navigation menu items for NetBox."""

from netbox.plugins import PluginMenuButton, PluginMenuItem

menu_items = (
    PluginMenuItem(
        link="plugins:netbox_barcode_plugin:scan",
        link_text="バーコードスキャン",
        buttons=(
            PluginMenuButton(
                link="plugins:netbox_barcode_plugin:scan",
                title="バーコードをスキャン",
                icon_class="mdi mdi-barcode-scan",
            ),
        ),
    ),
)
