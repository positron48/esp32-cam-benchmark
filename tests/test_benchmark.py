"""Tests for ESP32-CAM benchmark functionality.

This module contains tests for the ESP32-CAM benchmark runner,
including configuration loading, directory structure, and command generation.
"""

from unittest.mock import patch

import numpy as np
import pytest

from benchmark import ESPCamBenchmark


@pytest.fixture()
def benchmark_instance():
    """Create a benchmark instance for testing"""
    # Mock both port and IP functions
    with patch(
        "benchmark.utils.serial.find_esp_port", return_value="/dev/ttyUSB0"
    ), patch("benchmark.utils.serial.wait_for_ip", return_value="192.168.1.100"):
        return ESPCamBenchmark()


def test_config_loading(benchmark_instance):
    """Test that configuration file is loaded correctly"""
    assert benchmark_instance.config is not None
    assert "wifi" in benchmark_instance.config
    assert "camera_resolutions" in benchmark_instance.config
    assert "video_protocols" in benchmark_instance.config
    assert "control_protocols" in benchmark_instance.config


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
    test_params = {
        "video_protocol": "HTTP",
        "control_protocol": "UDP",
        "resolution": "VGA",
        "quality": 30,
        "metrics": True,
        "raw_mode": False,
    }
    cmd = benchmark_instance.build_firmware(test_params, dry_run=True)
    assert "--video=HTTP" in cmd
    assert "--control=UDP" in cmd
    assert "--resolution=VGA" in cmd
    assert "--quality=30" in cmd
    assert "--metrics=1" in cmd
    assert "--raw=0" in cmd


@patch("benchmark.benchmark.cv2")
@patch("benchmark.utils.serial.serial.Serial")
@patch("benchmark.utils.serial.wait_for_ip")
@patch("benchmark.utils.serial.find_esp_port")
def test_video_url_generation(
    mock_find_esp_port, mock_wait_for_ip, mock_serial, mock_cv2, benchmark_instance
):
    """Test that video stream URLs are correctly generated"""
    # Create a mock frame
    mock_frame = np.zeros((640, 480, 3), dtype=np.uint8)
    mock_cv2.imread.return_value = mock_frame

    # Set test parameters
    benchmark_instance.current_test_params = {"video_protocol": "HTTP"}
    # IP address should be obtained from wait_for_ip mock
    expected_ip = "192.168.1.100"  # This matches the mock in benchmark_instance fixture
    mock_wait_for_ip.return_value = expected_ip
    mock_find_esp_port.return_value = "/dev/ttyUSB0"
    benchmark_instance.config["wifi"]["device_ip"] = expected_ip

    # Configure mock
    mock_capture = mock_cv2.VideoCapture.return_value
    mock_capture.isOpened.return_value = True
    mock_capture.get.return_value = 640
    mock_capture.read.return_value = (True, mock_frame)
    mock_cv2.VideoWriter_fourcc.return_value = 0
    mock_cv2.CAP_PROP_FRAME_WIDTH = 3
    mock_cv2.CAP_PROP_FRAME_HEIGHT = 4
    mock_cv2.CAP_PROP_FPS = 5

    # Test HTTP URL
    benchmark_instance.capture_video(1, "test.mp4")
    mock_cv2.VideoCapture.assert_called_once()
    args = mock_cv2.VideoCapture.call_args[0]
    assert args[0] == f"http://{expected_ip}/video"

    # Test RTSP URL
    mock_cv2.VideoCapture.reset_mock()
    benchmark_instance.current_test_params = {"video_protocol": "RTSP"}
    benchmark_instance.capture_video(1, "test.mp4")
    mock_cv2.VideoCapture.assert_called_once()
    args = mock_cv2.VideoCapture.call_args[0]
    assert args[0] == f"rtsp://{expected_ip}:8554/stream"

    # Test UDP URL
    mock_cv2.VideoCapture.reset_mock()
    benchmark_instance.current_test_params = {"video_protocol": "UDP"}
    benchmark_instance.capture_video(1, "test.mp4")
    mock_cv2.VideoCapture.assert_called_once()
    args = mock_cv2.VideoCapture.call_args[0]
    assert args[0] == f"udp://{expected_ip}:5000"

    # Test WebRTC (should raise NotImplementedError)
    benchmark_instance.current_test_params = {"video_protocol": "WebRTC"}
    with pytest.raises(NotImplementedError):
        benchmark_instance.capture_video(1, "test.mp4")


@patch("benchmark.utils.serial.find_esp_port")
@patch("benchmark.utils.serial.serial.Serial")
@patch("benchmark.utils.serial.wait_for_ip")
def test_control_protocol(
    mock_wait_for_ip, mock_serial, mock_find_esp_port, benchmark_instance
):
    """Test control protocol functionality"""
    test_params = {
        "video_protocol": "HTTP",
        "control_protocol": "UDP",
        "resolution": "VGA",
        "quality": 30,
        "metrics": True,
        "raw_mode": False,
    }
    benchmark_instance.current_test_params = test_params

    # Mock find_esp_port to return a valid port
    mock_find_esp_port.return_value = "/dev/ttyUSB0"

    # Mock wait_for_ip to return a valid IP
    mock_wait_for_ip.return_value = "192.168.1.100"

    # Mock serial port behavior
    mock_serial_instance = mock_serial.return_value
    mock_serial_instance.__enter__.return_value = mock_serial_instance
    mock_serial_instance.readline.return_value = b"IP: 192.168.1.100\n"

    # Mock socket operations
    with patch("socket.socket") as mock_socket:
        mock_socket.return_value.recvfrom.return_value = (
            b"test data",
            ("127.0.0.1", 1234),
        )
        result = benchmark_instance.test_control(1)
        assert isinstance(result, dict)
        assert "latency" in result
        assert "success_rate" in result
        assert "errors" in result
        assert isinstance(result["latency"], list)
        assert isinstance(result["success_rate"], (int, float))
        assert isinstance(result["errors"], list)
