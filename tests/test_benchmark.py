"""Tests for ESP32-CAM benchmark functionality.

This module contains tests for the ESP32-CAM benchmark runner,
including configuration loading, directory structure, and command generation.
"""

from pathlib import Path

import pytest

from run_tests import ESPCamBenchmark


@pytest.fixture
def benchmark_instance():
    """Create a benchmark instance for testing"""
    return ESPCamBenchmark()


def test_config_loading(benchmark_instance):
    """Test that configuration file is loaded correctly"""
    assert benchmark_instance.config is not None
    assert "wifi" in benchmark_instance.config
    assert "camera_resolutions" in benchmark_instance.config
    assert "video_protocols" in benchmark_instance.config
    assert "control_protocols" in benchmark_instance.config


def test_results_directories():
    """Test that results directories are created"""
    results_dir = Path("results")
    video_dir = results_dir / "video"
    logs_dir = results_dir / "logs"
    metrics_dir = results_dir / "metrics"

    assert results_dir.exists()
    assert video_dir.exists()
    assert logs_dir.exists()
    assert metrics_dir.exists()


def test_protocol_combinations(benchmark_instance):
    """Test that protocol combinations are generated correctly"""
    test_params = {
        "video_protocol": "HTTP",
        "control_protocol": "UDP",
        "resolution": "VGA",
        "quality": 30,
        "metrics": True,
        "raw_mode": False,
    }
    cmd = benchmark_instance.build_firmware(test_params, dry_run=True)
    assert isinstance(cmd, list)
    assert all(isinstance(arg, str) for arg in cmd)


def test_build_parameters(benchmark_instance):
    """Test that build parameters are correctly formatted"""
    params = {
        "video_protocol": "HTTP",
        "control_protocol": "UDP",
        "resolution": "VGA",
        "quality": 30,
        "metrics": True,
        "raw_mode": False,
    }
    cmd = benchmark_instance.build_firmware(params, dry_run=True)
    assert isinstance(cmd, list)
    assert len(cmd) == 7
    assert cmd[0] == "./build_firmware.sh"
    assert cmd[1] == "--video=HTTP"
    assert cmd[2] == "--control=UDP"
    assert cmd[3] == "--resolution=VGA"
    assert cmd[4] == "--quality=30"
    assert cmd[5] == "--metrics=1"
    assert cmd[6] == "--raw=0"
