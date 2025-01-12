"""Main benchmark class for ESP32-CAM testing."""

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
import os

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

        # Store current test parameters for build
        self.current_test_params = test_params

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

        # Save metrics to file
        metrics_dir = Path("results/metrics")
        metrics_dir.mkdir(parents=True, exist_ok=True)
        metrics_file = metrics_dir / config.generate_file_name(test_params, "metrics", "json")
        
        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump({
                "parameters": test_params,
                "results": results
            }, f, indent=2)
        
        self.logger.info("Metrics saved to: %s", metrics_file)

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
            # Prepare build flags based on current test parameters
            build_flags = []
            if hasattr(self, 'current_test_params'):
                if self.current_test_params.get("video_protocol"):
                    build_flags.append(f"-DVIDEO_PROTOCOL={self.current_test_params['video_protocol']}")
                if self.current_test_params.get("control_protocol"):
                    build_flags.append(f"-DCONTROL_PROTOCOL={self.current_test_params['control_protocol']}")
                if self.current_test_params.get("resolution"):
                    build_flags.append(f"-DCAMERA_RESOLUTION={self.current_test_params['resolution']}")
                if self.current_test_params.get("quality"):
                    build_flags.append(f"-DJPEG_QUALITY={self.current_test_params['quality']}")
                # Always set ENABLE_METRICS based on test_params
                build_flags.append(f"-DENABLE_METRICS={1 if self.current_test_params.get('metrics') else 0}")
                if self.current_test_params.get("raw_mode"):
                    build_flags.append("-DRAW_MODE=1")
            
            # Set environment variable with build flags
            env = os.environ.copy()
            if build_flags:
                env["PLATFORMIO_BUILD_FLAGS"] = " ".join(build_flags)
                self.logger.info("Build flags: %s", env["PLATFORMIO_BUILD_FLAGS"])

            # Find ESP32 port
            port = serial.find_esp_port()
            if not port:
                raise RuntimeError("ESP32-CAM not found")

            # Build and upload in one command
            self.logger.info("Building and flashing firmware...")
            subprocess.run(["pio", "run", "-t", "upload", "--upload-port", port], env=env, check=True)
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to build/flash firmware: {e}") from e

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