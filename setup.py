"""Setup script for ESP32-CAM benchmark package."""

from setuptools import find_packages, setup

setup(
    name="esp32cam-benchmark",
    version="0.1.0",
    description="ESP32-CAM benchmark tool",
    author="Cursor",
    author_email="info@cursor.sh",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "esp32cam-benchmark=benchmark.cli:main",
        ],
    },
    python_requires=">=3.8",
)