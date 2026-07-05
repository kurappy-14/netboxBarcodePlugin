from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_mit_license_exists():
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")

    assert "MIT License" in text
    assert "Permission is hereby granted" in text


def test_third_party_license_mentions_html5_qrcode():
    text = (ROOT / "THIRD_PARTY_LICENSES.md").read_text(encoding="utf-8")

    assert "html5-qrcode" in text
    assert "Apache License" in text or "Apache-2.0" in text


def test_setup_mentions_mit_license():
    text = (ROOT / "setup.py").read_text(encoding="utf-8")

    assert 'license="MIT"' in text
