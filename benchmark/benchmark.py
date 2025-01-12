"""Main benchmark class for ESP32-CAM testing."""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List

import cv2

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
        self.current_test_params = None

    def run_test_combination(
        self, test_params: Dict[str, Any], skip_build: bool = False
    ) -> Dict[str, Any]:
        """Run a single test with specified parameters.

        Args:
            test_params: Dictionary with test parameters
            skip_build: Whether to skip firmware build and flash

        Returns:
            Dictionary with test results
        """
        # Validate test parameters
        if test_params.get("raw_mode") and test_params.get("video_protocol") == "HTTP":
            raise ValueError(
                "HTTP protocol is not supported in RAW mode. Please use a different video protocol or disable RAW mode."
            )

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
                self.logger,
            )

        # Run control test if protocol specified
        if test_params.get("control_protocol"):
            results["control"] = control.test_control(
                ip_address,
                test_params["control_protocol"],
                self.config["test_duration"],
                self.logger,
            )

        # Save metrics to file
        metrics_dir = Path("results/metrics")
        metrics_dir.mkdir(parents=True, exist_ok=True)
        metrics_file = metrics_dir / config.generate_file_name(
            test_params, "metrics", "json"
        )

        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump({"parameters": test_params, "results": results}, f, indent=2)

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
                results.append({"params": test_params, "results": result})
            except Exception as e:
                self.logger.error("Test failed: %s", str(e))
                results.append({"params": test_params, "error": str(e)})
        return results

    def _build_and_flash(self) -> None:
        """Build and flash firmware."""
        self.logger.info("Building firmware...")
        try:
            # Prepare build flags based on current test parameters
            build_flags = []
            if hasattr(self, "current_test_params"):
                if self.current_test_params.get("video_protocol"):
                    build_flags.append(
                        f"-DVIDEO_PROTOCOL={self.current_test_params['video_protocol']}"
                    )
                if self.current_test_params.get("control_protocol"):
                    build_flags.append(
                        f"-DCONTROL_PROTOCOL={self.current_test_params['control_protocol']}"
                    )
                if self.current_test_params.get("resolution"):
                    build_flags.append(
                        f"-DCAMERA_RESOLUTION={self.current_test_params['resolution']}"
                    )
                if self.current_test_params.get("quality"):
                    build_flags.append(
                        f"-DJPEG_QUALITY={self.current_test_params['quality']}"
                    )
                # Always set ENABLE_METRICS based on test_params
                build_flags.append(
                    f"-DENABLE_METRICS={1 if self.current_test_params.get('metrics') else 0}"
                )
                build_flags.append(
                    f"-DRAW_MODE={1 if self.current_test_params.get('raw_mode') else 0}"
                )

            # Set environment variable with build flags
            env = os.environ.copy()
            if build_flags:
                env["PLATFORMIO_BUILD_FLAGS"] = " ".join(build_flags)
                self.logger.info("Build flags: %s", env["PLATFORMIO_BUILD_FLAGS"])

            # Find ESP32 port
            port = serial.find_esp_port()
            if not port:
                raise RuntimeError("ESP32-CAM not found")

            # Select build environment based on metrics
            build_env = (
                "esp32cam_with_metrics"
                if self.current_test_params.get("metrics")
                else "esp32cam"
            )
            self.logger.info("Using build environment: %s", build_env)

            # Build and upload in one command
            self.logger.info("Building and flashing firmware...")
            subprocess.run(
                ["pio", "run", "-e", build_env, "-t", "upload", "--upload-port", port],
                env=env,
                check=True,
            )

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
                        for raw_mode in [True, False]:
                            # Skip HTTP protocol in RAW mode
                            if raw_mode and protocol == "HTTP":
                                continue

                            combinations.append(
                                {
                                    "video_protocol": protocol,
                                    "resolution": resolution,
                                    "quality": quality,
                                    "control_protocol": ctrl_protocol,
                                    "metrics": True,
                                    "raw_mode": raw_mode,
                                }
                            )
        return combinations

    def build_firmware(
        self, test_params: Dict[str, Any], dry_run: bool = False
    ) -> List[str]:
        """Build firmware with specified parameters.

        Args:
            test_params: Dictionary with test parameters
            dry_run: If True, return command that would be executed

        Returns:
            Command that would be executed if dry_run is True
        """
        build_flags = []
        if test_params.get("video_protocol"):
            build_flags.append(f"--video={test_params['video_protocol']}")
        if test_params.get("control_protocol"):
            build_flags.append(f"--control={test_params['control_protocol']}")
        if test_params.get("resolution"):
            build_flags.append(f"--resolution={test_params['resolution']}")
        if test_params.get("quality"):
            build_flags.append(f"--quality={test_params['quality']}")
        build_flags.append(f"--metrics={1 if test_params.get('metrics') else 0}")
        build_flags.append(f"--raw={1 if test_params.get('raw_mode') else 0}")

        build_env = (
            "esp32cam_with_metrics" if test_params.get("metrics") else "esp32cam"
        )
        cmd = ["pio", "run", "-e", build_env]
        if not dry_run:
            cmd.extend(["-t", "upload"])
        cmd.extend(build_flags)

        if build_flags:
            os.environ["PLATFORMIO_BUILD_FLAGS"] = " ".join(build_flags)

        return cmd

    def test_control(self, duration: int) -> Dict[str, Any]:
        """Run control protocol test.

        Args:
            duration: Test duration in seconds

        Returns:
            Dictionary with test results
        """
        if not hasattr(self, "current_test_params"):
            raise RuntimeError("No test parameters set")

        port = serial.find_esp_port()
        if not port:
            raise RuntimeError("ESP32-CAM not found")

        ip_address = serial.wait_for_ip(port)
        if not ip_address:
            raise RuntimeError("Failed to get device IP address")

        return control.test_control(
            ip_address,
            self.current_test_params["control_protocol"],
            duration,
            self.logger,
        )

    def capture_video(self, duration: int, output_file: str) -> None:
        """Capture video from the device.

        Args:
            duration: Duration to capture in seconds
            output_file: Output file path
        """
        if not hasattr(self, "current_test_params"):
            raise RuntimeError("No test parameters set")

        port = serial.find_esp_port()
        if not port:
            raise RuntimeError("ESP32-CAM not found")

        ip_address = serial.wait_for_ip(port)
        if not ip_address:
            raise RuntimeError("Failed to get device IP address")

        # Construct video URL based on protocol
        if self.current_test_params["video_protocol"] == "HTTP":
            url = f"http://{ip_address}/video"
        elif self.current_test_params["video_protocol"] == "RTSP":
            url = f"rtsp://{ip_address}:8554/stream"
        elif self.current_test_params["video_protocol"] == "UDP":
            url = f"udp://{ip_address}:5000"
        elif self.current_test_params["video_protocol"] == "WebRTC":
            raise NotImplementedError("WebRTC video capture not implemented yet")
        else:
            raise ValueError(
                f"Unsupported video protocol: {self.current_test_params['video_protocol']}"
            )

        # Open video capture
        cap = cv2.VideoCapture(url)
        if not cap.isOpened():
            raise RuntimeError("Failed to open video stream")

        # Get video properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))

        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(output_file, fourcc, fps, (width, height))

        # Capture frames
        start_time = time.time()
        while (time.time() - start_time) < duration:
            ret, frame = cap.read()
            if not ret:
                break
            out.write(frame)

        # Release resources
        cap.release()
        out.release()
