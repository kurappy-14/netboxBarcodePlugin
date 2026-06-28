from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_html5_qrcode_exists_locally():
    path = ROOT / "netbox_barcode_plugin/static/netbox_barcode_plugin/js/html5-qrcode.min.js"

    assert path.exists()
    assert path.stat().st_size > 1000


def test_template_loads_local_html5_qrcode():
    template = ROOT / "netbox_barcode_plugin/templates/netbox_barcode_plugin/scan.html"
    text = template.read_text(encoding="utf-8")

    assert "netbox_barcode_plugin/js/html5-qrcode.min.js" in text


def test_no_external_cdn_references_in_frontend_or_docs():
    banned = ("cdn.jsdelivr.net", "unpkg.com", "cdnjs.cloudflare.com")
    paths = [
        ROOT / "README.md",
        ROOT / "netbox_barcode_plugin/templates/netbox_barcode_plugin/scan.html",
        ROOT / "netbox_barcode_plugin/static/netbox_barcode_plugin/js/barcode_scanner.js",
    ]

    for path in paths:
        text = path.read_text(encoding="utf-8")
        for banned_text in banned:
            assert banned_text not in text


def test_frontend_uses_csrf_header():
    js = (ROOT / "netbox_barcode_plugin/static/netbox_barcode_plugin/js/barcode_scanner.js").read_text(
        encoding="utf-8"
    )

    assert "X-CSRFToken" in js
    assert "getCookie(\"csrftoken\")" in js


def test_frontend_prefers_text_content_for_api_values():
    js = (ROOT / "netbox_barcode_plugin/static/netbox_barcode_plugin/js/barcode_scanner.js").read_text(
        encoding="utf-8"
    )

    assert ".textContent" in js
    assert ".innerHTML" not in js
