"""Configuration utilities for ESP32-CAM benchmark."""

import os
from pathlib import Path
from typing import Any, Dict

import yaml
from dotenv import load_dotenv


def load_config(config_file: str) -> Dict[str, Any]:
    """Load configuration with environment variable substitution.

    Args:
        config_file: Path to the YAML configuration file

    Returns:
        Dictionary with configuration values
    """
    # Load environment variables from .env file
    env_path = Path(".env")
    if env_path.exists():
        load_dotenv(env_path)

    # Load YAML with environment variable substitution
    with open(config_file, encoding="utf-8") as f:
        # Replace environment variables in the YAML content
        content = f.read()
        for key, value in os.environ.items():
            content = content.replace(f"${{{key}}}", value)
        return yaml.safe_load(content)


def generate_file_name(test_params: Dict[str, Any], file_type: str, extension: str) -> str:
    """Generate a standardized file name with all relevant parameters.

    Args:
        test_params: Test parameters
        file_type: Type of file (video/metrics/log)
        extension: File extension without dot

    Returns:
        Formatted file name with parameters
    """
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    params = []

    if test_params.get("video_protocol"):
        params.append(f"vid_{test_params['video_protocol']}")
    if test_params.get("control_protocol"):
        params.append(f"ctrl_{test_params['control_protocol']}")
    if test_params.get("resolution"):
        params.append(f"res_{test_params['resolution']}")
    if test_params.get("quality"):
        params.append(f"q{test_params['quality']}")
    if test_params.get("metrics"):
        params.append("metrics")
    if test_params.get("raw_mode"):
        params.append("raw")

    return f"{file_type}_{timestamp}_{'_'.join(params)}.{extension}"