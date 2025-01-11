#!/usr/bin/env python3
"""ESP32-CAM benchmark test runner.

This module provides functionality to run various benchmarks for ESP32-CAM,
including video streaming and control protocol testing.
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2  # type: ignore
import serial
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


def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(
                f'results/logs/benchmark_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
            ),
        ],
    )
    return logging.getLogger("ESP32-CAM-Benchmark")


def find_esp_port() -> Optional[str]:
    """Find ESP32 COM port.

    Returns:
        String with port name or None if not found
    """
    import serial.tools.list_ports

    # Common ESP32 USB-UART bridge chips
    esp_chips = {
        "CP210x": "Silicon Labs CP210x",
        "CH340": "USB-Serial CH340",
        "FTDI": "FTDI",
        "USB2Serial": "USB2Serial",
        "USB-Serial": "USB-Serial",
        "USB Serial": "USB Serial",
        "ACM": "ttyACM",
    }

    ports = serial.tools.list_ports.comports()
    logging.debug("Found serial ports:")
    for port in ports:
        logging.debug(
            f"Port: {port.device}, Description: {port.description}, HW ID: {port.hwid}"
        )
        for _, chip_id in esp_chips.items():
            if (
                chip_id.lower() in port.description.lower()
                or chip_id.lower() in port.hwid.lower()
            ):
                return port.device
    return None


def flash_firmware(firmware_path: str, port: str) -> None:
    """Flash firmware to ESP32-CAM.

    Args:
        firmware_path: Path to firmware binary
        port: COM port to use

    Raises:
        RuntimeError: If flashing fails
    """
    cmd = ["pio", "run", "--target", "upload"]

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to flash firmware: {e.stdout}") from e


def wait_for_ip(port: str, timeout: int = 30) -> Optional[str]:
    """Wait for IP address from ESP32 serial output.

    Args:
        port: COM port to read from
        timeout: Maximum time to wait in seconds

    Returns:
        IP address string or None if not found
    """
    with serial.Serial(port, 115200, timeout=1, rtscts=False, dsrdtr=False) as ser:
        # Set RTS and DTR to 0 as specified in platformio.ini
        ser.setRTS(False)
        ser.setDTR(False)

        start_time = time.time()
        ip_pattern = re.compile(r"http://(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})")

        while (time.time() - start_time) < timeout:
            if ser.in_waiting:
                line = ser.readline().decode("utf-8", errors="ignore")
                logging.debug("Serial output: %s", line.strip())
                match = ip_pattern.search(line)
                if match:
                    return match.group(1)
            time.sleep(0.1)
    return None


class ESPCamBenchmark:
    """ESP32-CAM benchmark test runner.

    This class provides methods to build firmware with different configurations
    and run various benchmarks including video streaming and control protocols.
    """

    def __init__(self, config_file="bench_config.yml"):
        """Initialize benchmark runner.

        Args:
            config_file: Path to the configuration file
        """
        self.logger = setup_logging()
        self.logger.info("Initializing ESP32-CAM Benchmark Runner")

        # Load configuration with environment variables
        self.config = load_config(config_file)
        self.logger.info("Configuration loaded successfully")

        # Find ESP32 port
        self.port = find_esp_port()
        if not self.port:
            self.logger.error("ESP32-CAM not found. Please check connection")
            raise RuntimeError("ESP32-CAM not found")
        self.logger.info("Found ESP32-CAM on port %s", self.port)

        # Verify required configuration
        if not all(self.config["wifi"].get(key) for key in ["ssid", "password"]):
            self.logger.error(
                "Missing required WiFi configuration. Please check your .env file"
            )
            raise ValueError("Missing WiFi configuration")

    def build_firmware(
        self,
        params: Dict[str, Any],
        dry_run: bool = False,
    ) -> List[str]:
        """Build firmware with specified parameters

        Args:
            params: Dictionary with build parameters
            dry_run: If True, only return the command without executing it

        Returns:
            List of command arguments
        """
        self.logger.info("Building firmware with parameters: %s", params)
        cmd = [
            "./build_firmware.sh",
            f'--video={params["video_protocol"]}',
            f'--control={params["control_protocol"]}',
            f'--resolution={params["resolution"]}',
            f'--quality={params["quality"]}',
            f'--metrics={1 if params["metrics"] else 0}',
            f'--raw={1 if params.get("raw_mode", False) else 0}',
        ]

        if dry_run:
            self.logger.info("Dry run - command: %s", " ".join(cmd))
            return cmd

        try:
            self.logger.info("Executing build command: %s", " ".join(cmd))
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            self.logger.info("Build completed successfully")
            if result.stdout:
                self.logger.debug("Build output: %s", result.stdout)
            return cmd
        except subprocess.CalledProcessError as e:
            self.logger.error("Build failed: %s", e.stdout)
            raise RuntimeError(f"Build failed: {e.stdout}") from e

    def capture_video(self, duration: int, output_path: str) -> None:
        """Capture video stream from ESP32-CAM"""
        self.logger.info(
            "Starting video capture for %d seconds to %s", duration, output_path
        )

        # Get ESP32-CAM IP address from WiFi connection
        esp32_ip = wait_for_ip(self.port)
        if not esp32_ip:
            raise RuntimeError("Failed to get ESP32-CAM IP address")

        # Construct video stream URL based on protocol
        if not hasattr(self, "current_test_params") or not self.current_test_params:
            raise ValueError("No test parameters set. Call run_test_combination first.")

        # Construct video stream URL based on protocol
        stream_url = None
        if self.current_test_params["video_protocol"] == "HTTP":
            stream_url = f"http://{esp32_ip}:80/stream"
        elif self.current_test_params["video_protocol"] == "RTSP":
            stream_url = f"rtsp://{esp32_ip}:8554/stream"
        elif self.current_test_params["video_protocol"] == "WebRTC":
            self.logger.error("WebRTC capture not implemented yet")
            raise NotImplementedError("WebRTC capture not implemented")
        elif self.current_test_params["video_protocol"] == "UDP":
            stream_url = f"udp://{esp32_ip}:5000"

        if not stream_url:
            self.logger.error("Invalid video protocol or stream URL")
            raise ValueError("Invalid video protocol or stream URL")

        self.logger.info("Connecting to video stream at %s", stream_url)
        try:
            cap = cv2.VideoCapture(stream_url)
            if not cap.isOpened():
                self.logger.error("Failed to open video stream")
                raise RuntimeError("Failed to open video stream")
        except Exception as e:
            self.logger.error("Error opening video stream: %s", str(e))
            raise RuntimeError(f"Error opening video stream: {str(e)}") from e

        # Get video properties
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))

        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))

        start_time = time.time()
        while (time.time() - start_time) < duration:
            ret, frame = cap.read()
            if not ret:
                break
            out.write(frame)

        cap.release()
        out.release()
        self.logger.info("Video capture completed")

    def test_control(self, duration: int) -> Dict[str, Any]:
        """Test control commands"""
        self.logger.info("Starting control protocol test for %d seconds", duration)
        results = {"latency": [], "success_rate": 0, "errors": []}

        commands_sent = 0
        start_time = time.time()
        while (time.time() - start_time) < duration:
            try:
                # Send test commands and measure response time
                cmd_start = time.time()
                # TODO: Implement actual control command testing
                cmd_end = time.time()
                latency = cmd_end - cmd_start
                results["latency"].append(latency)
                commands_sent += 1
                if commands_sent % 10 == 0:  # Log every 10 commands
                    self.logger.debug(
                        "Sent %d commands, last latency: %.3f ms",
                        commands_sent,
                        latency * 1000,
                    )
            except Exception as e:
                self.logger.error("Control command failed: %s", str(e))
                results["errors"].append(str(e))

        total_commands = len(results["latency"]) + len(results["errors"])
        if total_commands > 0:
            results["success_rate"] = len(results["latency"]) / total_commands
            avg_latency = (
                sum(results["latency"]) / len(results["latency"])
                if results["latency"]
                else 0
            )
            self.logger.info(
                "Control test completed: %d/%d successful commands (%.1f%%), avg latency: %.3f ms",
                len(results["latency"]),
                total_commands,
                results["success_rate"] * 100,
                avg_latency * 1000,
            )

        return results

    def run_test_combination(self, test_params: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test combination"""
        self.logger.info("Starting test with parameters: %s", test_params)
        self.current_test_params = test_params
        results = {
            "params": test_params,
            "timestamp": datetime.now().isoformat(),
            "video_metrics": {},
            "control_metrics": {},
            "errors": [],
        }

        try:
            # Build firmware
            self.build_firmware(test_params)

            # Flash firmware
            firmware_path = ".pio/build/esp32cam/firmware.bin"
            self.logger.info("Flashing firmware to ESP32-CAM...")
            flash_firmware(firmware_path, self.port)

            # Wait for device to boot and get IP
            self.logger.info("Waiting for device to boot and get IP...")
            ip_address = wait_for_ip(self.port)
            if not ip_address:
                raise RuntimeError("Failed to get device IP address")
            self.logger.info("Device IP address: %s", ip_address)

            # Update config with actual IP
            self.config["wifi"]["device_ip"] = ip_address

            # Wait additional time for all services to start
            time.sleep(self.config.get("warmup_time", 5))

            # Run video capture test if enabled
            if test_params.get("video_protocol"):
                video_path = (
                    f"results/video/{test_params['video_protocol']}_"
                    f"{test_params['resolution']}_{test_params['quality']}.mp4"
                )
                self.capture_video(self.config["test_duration"], video_path)

                results["video_metrics"] = {
                    "path": video_path,
                    "duration": self.config["test_duration"],
                    "protocol": test_params["video_protocol"],
                    "resolution": test_params["resolution"],
                    "quality": test_params["quality"],
                }

            # Run control test if enabled
            if test_params.get("control_protocol"):
                results["control_metrics"] = self.test_control(
                    self.config["test_duration"]
                )

            self.logger.info("Test completed successfully")

        except Exception as e:
            self.logger.error("Test failed: %s", str(e))
            results["errors"].append(str(e))

        return results

    def run_all_tests(self) -> List[Dict[str, Any]]:
        """Run all test combinations"""
        all_results = []

        try:
            for test_group in self.config["test_combinations"]:
                for test in test_group["tests"]:
                    # Generate parameter combinations
                    video_protocols = (
                        self.config["video_protocols"]
                        if test["video_protocol"] == "all"
                        else [test["video_protocol"]]
                    )
                    control_protocols = (
                        self.config["control_protocols"]
                        if test["control_protocol"] == "all"
                        else [test["control_protocol"]]
                    )
                    resolutions = (
                        self.config["camera_resolutions"]
                        if test["resolutions"] == "all"
                        else test["resolutions"]
                    )
                    qualities = (
                        self.config["jpeg_qualities"]
                        if test["qualities"] == "all"
                        else test["qualities"]
                    )

                    # Run tests for each combination
                    for video_protocol in video_protocols:
                        for control_protocol in control_protocols:
                            for resolution in resolutions:
                                for quality in qualities:
                                    for metrics in test["metrics"]:
                                        for raw_mode in test["raw_mode"]:
                                            params = {
                                                "video_protocol": video_protocol,
                                                "control_protocol": control_protocol,
                                                "resolution": resolution,
                                                "quality": quality,
                                                "metrics": metrics,
                                                "raw_mode": raw_mode,
                                            }
                                            results = self.run_test_combination(params)
                                            all_results.append(results)

                                            # Save results after each test
                                            self._save_results(results)

        except Exception as e:
            print(f"Error running tests: {e}")

        return all_results

    def _save_results(self, results: Dict[str, Any]) -> None:
        """Save test results to file.

        Args:
            results: Dictionary containing test results
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = f"results/logs/test_{timestamp}.json"

        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="ESP32-CAM Benchmark Runner")
    parser.add_argument(
        "--single-test",
        action="store_true",
        help="Run a single test with specified parameters",
    )
    parser.add_argument(
        "--video-protocol",
        choices=["HTTP", "RTSP", "UDP", "WebRTC", "none"],
        help="Video protocol to use",
    )
    parser.add_argument(
        "--control-protocol",
        choices=["HTTP", "UDP", "WebSocket", "none"],
        help="Control protocol to use",
    )
    parser.add_argument(
        "--resolution",
        choices=["QQVGA", "QVGA", "VGA", "SVGA", "XGA", "SXGA", "UXGA"],
        help="Camera resolution",
    )
    parser.add_argument(
        "--quality", type=int, choices=range(10, 61, 10), help="JPEG quality (10-60)"
    )
    parser.add_argument(
        "--metrics", action="store_true", help="Enable metrics collection"
    )
    parser.add_argument("--raw-mode", action="store_true", help="Enable raw mode")
    parser.add_argument("--duration", type=int, help="Test duration in seconds")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    benchmark = ESPCamBenchmark()

    if args.single_test:
        if not all(
            [args.video_protocol, args.control_protocol, args.resolution, args.quality]
        ):
            print(
                "Error: When running a single test, you must specify all test parameters:"
            )
            print("  --video-protocol, --control-protocol, --resolution, --quality")
            exit(1)

        test_params = {
            "video_protocol": (
                args.video_protocol if args.video_protocol != "none" else None
            ),
            "control_protocol": (
                args.control_protocol if args.control_protocol != "none" else None
            ),
            "resolution": args.resolution,
            "quality": args.quality,
            "metrics": args.metrics,
            "raw_mode": args.raw_mode,
        }

        if args.duration:
            benchmark.config["test_duration"] = args.duration

        print(
            f"Running single test with parameters: {json.dumps(test_params, indent=2)}"
        )
        results = benchmark.run_test_combination(test_params)
        print(f"Test results: {json.dumps(results, indent=2)}")
    else:
        results = benchmark.run_all_tests()
