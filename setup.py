"""Packaging definition for netbox-barcode-plugin."""
from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="netbox-barcode-plugin",
    version="0.1.0",
    description="NetBox plugin to scan barcodes and view/update Cable status from a smartphone.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="kurappy_",
    license="MIT",
    url="https://github.com/kurappy-14/netboxBarcodePlugin",
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    zip_safe=False,
    python_requires=">=3.10",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Framework :: Django",
    ],
)
