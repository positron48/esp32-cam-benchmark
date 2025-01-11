"""Main benchmark class for ESP32-CAM testing."""

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from .protocols import control, video
from .utils import config, logging, serial


class ESPCamBenchmark:
    """Main benchmark class for ESP32-CAM testing."""

    def __init__(self):
        """Initialize benchmark instance."""
        self.logger = logging.setup_logging()
        self.config = config.load_config("bench_config.yml")
        self.results_dir = Path("results")
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def run_test_combination(self, test_params: Dict[str, Any], skip_build: bool = False) -> Dict[str, Any]:
        """Run a single test with specified parameters.

        Args:
            test_params: Dictionary with test parameters
            skip_build: Whether to skip firmware build and flash

        Returns:
            Dictionary with test results
        """
        self.logger.info("Starting test with parameters: %s", test_params)
        results = {}

        if not skip_build:
            self._build_and_flash()

        # Find ESP32 port
        port = serial.find_esp_port()
        if not port:
            raise RuntimeError("ESP32-CAM not found")

        # Wait for device to initialize and get IP
        ip_address = serial.wait_for_ip(port)
        if not ip_address:
            raise RuntimeError("Failed to get device IP address")

        self.logger.info("Device IP: %s", ip_address)

        # Run video test if protocol specified
        if test_params.get("video_protocol"):
            results["video"] = video.test_video(
                ip_address,
                test_params["video_protocol"],
                test_params["resolution"],
                test_params["quality"],
                test_params.get("raw_mode", False),
                self.config["test_duration"],
                self.logger
            )

        # Run control test if protocol specified
        if test_params.get("control_protocol"):
            results["control"] = control.test_control(
                ip_address,
                test_params["control_protocol"],
                self.config["test_duration"],
                self.logger
            )

        return results

    def run_all_tests(self) -> List[Dict[str, Any]]:
        """Run all test combinations from config.

        Returns:
            List of dictionaries with test results
        """
        results = []
        for test_params in self._generate_test_combinations():
            try:
                result = self.run_test_combination(test_params)
                results.append({
                    "params": test_params,
                    "results": result
                })
            except Exception as e:
                self.logger.error("Test failed: %s", str(e))
                results.append({
                    "params": test_params,
                    "error": str(e)
                })
        return results

    def _build_and_flash(self) -> None:
        """Build and flash firmware."""
        self.logger.info("Building firmware...")
        try:
            subprocess.run(["pio", "run"], check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to build firmware: {e}") from e

        self.logger.info("Flashing firmware...")
        port = serial.find_esp_port()
        if not port:
            raise RuntimeError("ESP32-CAM not found")

        try:
            serial.flash_firmware(port)
        except Exception as e:
            raise RuntimeError(f"Failed to flash firmware: {e}") from e

    def _generate_test_combinations(self) -> List[Dict[str, Any]]:
        """Generate all test combinations from config.

        Returns:
            List of dictionaries with test parameters
        """
        combinations = []
        cfg = self.config["test_combinations"]

        for protocol in cfg["video_protocols"]:
            for resolution in cfg["resolutions"]:
                for quality in cfg["qualities"]:
                    for ctrl_protocol in cfg["control_protocols"]:
                        combinations.append({
                            "video_protocol": protocol,
                            "resolution": resolution,
                            "quality": quality,
                            "control_protocol": ctrl_protocol,
                            "metrics": True
                        })
        return combinations