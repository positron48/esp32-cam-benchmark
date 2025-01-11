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
import serial.tools.list_ports
import yaml
from dotenv import load_dotenv
import statistics


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
    # Ensure log directory exists
    log_dir = Path("results/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

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
            "Port: %(device)s, Description: %(desc)s, HW ID: %(hwid)s",
            {"device": port.device, "desc": port.description, "hwid": port.hwid},
        )
        for _, chip_id in esp_chips.items():
            if (
                chip_id.lower() in port.description.lower()
                or chip_id.lower() in port.hwid.lower()
            ):
                return port.device
    return None


def flash_firmware(port: str) -> None:
    """Flash firmware to ESP32-CAM.

    Args:
        port: COM port to use

    Raises:
        RuntimeError: If flashing fails
    """
    cmd = ["pio", "run", "--target", "upload", "--upload-port", port]

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
        init_found = False

        while (time.time() - start_time) < timeout:
            if ser.in_waiting:
                line = ser.readline().decode("utf-8", errors="ignore")
                
                # Wait for initialization message before processing output
                if not init_found:
                    if "Initialization" in line:
                        init_found = True
                        logging.debug("Found initialization message")
                    continue

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

        # Initialize current test parameters
        self.current_test_params = {}

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

    def capture_video(self, duration: int, output_path: str) -> Dict[str, Any]:
        """Capture video stream from ESP32-CAM"""
        # Add 2 seconds for incomplete first and last seconds
        actual_duration = duration + 2
        
        metrics = {
            "connection_time": 0,
            "total_frames": 0,
            "avg_fps": 0,
            "dropped_frames": 0,
            "total_size_mb": 0,
            "bitrate_mbps": 0,
            "test_duration": 0,
            "frames_per_second": []  # Frames captured in each second
        }
        
        test_start = time.time()
        self.logger.info(
            "Starting video capture for %d seconds (plus 2 seconds for incomplete data)", 
            duration
        )

        # Get ESP32-CAM IP address from WiFi connection
        esp32_ip = self.config["wifi"].get("device_ip")
        if not esp32_ip:
            raise RuntimeError("Device IP address not set. Run initialization first.")

        # Construct video stream URL based on protocol
        if not hasattr(self, "current_test_params") or not self.current_test_params:
            raise ValueError("No test parameters set. Call run_test_combination first.")

        # Construct video stream URL based on protocol
        stream_url = None
        if self.current_test_params["video_protocol"] == "HTTP":
            stream_url = f"http://{esp32_ip}:80/video"
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

        connection_start = time.time()
        self.logger.info("Connecting to video stream at %s", stream_url)
        try:
            self.logger.debug("Opening video capture...")
            cap = cv2.VideoCapture(stream_url)
            if not cap.isOpened():
                self.logger.error("Failed to open video stream")
                raise RuntimeError("Failed to open video stream")
            self.logger.info("Successfully connected to video stream")
        except Exception as e:
            self.logger.error("Error opening video stream: %s", str(e))
            raise RuntimeError(f"Error opening video stream: {str(e)}") from e

        metrics["connection_time"] = time.time() - connection_start

        # Get video properties
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        self.logger.info("Video properties: %dx%d @ %d fps", frame_width, frame_height, fps)

        # Create video writer
        self.logger.debug("Initializing video writer...")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))
        self.logger.info("Video writer initialized")

        frames_captured = 0
        failed_reads = 0
        start_time = time.time()
        last_frame_time = start_time
        frame_times = []
        frames_by_second = {}  # Временный буфер для подсчета кадров
        first_frame = True
        last_log_second = -1
        last_log_frames = 0

        while (time.time() - start_time) < actual_duration:
            ret, frame = cap.read()
            current_time = time.time()
            elapsed = current_time - start_time
            
            # Skip partial first second
            if first_frame:
                first_frame = False
                continue
            
            if not ret:
                self.logger.error("Failed to read frame at %.2f seconds", elapsed)
                failed_reads += 1
                continue
                
            # Определяем, к какой секунде относится кадр
            second = int(elapsed)
            if second not in frames_by_second:
                frames_by_second[second] = {"frames": 0, "dropped": 0}
            frames_by_second[second]["frames"] += 1
            
            frames_captured += 1
            
            # Calculate frame time
            frame_times.append(current_time - last_frame_time)
            last_frame_time = current_time
            
            out.write(frame)
            
            # Log statistics every second
            if second > last_log_second and second > 0:
                frames_this_second = frames_captured - last_log_frames
                avg_fps = frames_captured/elapsed
                self.logger.info("Second %d: captured %d frames (avg: %.2f)", 
                               second, frames_this_second, avg_fps)
                last_log_second = second
                last_log_frames = frames_captured

        cap.release()
        out.release()
        
        # Преобразуем собранную статистику в список по секундам
        # Пропускаем первую и последнюю секунды
        sorted_seconds = sorted(frames_by_second.keys())
        for second in sorted_seconds:
            if second > 0 and second <= duration:  # Используем только полные секунды в пределах duration
                metrics["frames_per_second"].append({
                    "second": second,
                    "frames": frames_by_second[second]["frames"],
                    "dropped": frames_by_second[second]["dropped"]
                })
        
        # Calculate final metrics
        test_duration = time.time() - test_start
        file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
        
        # Calculate frame time percentiles
        if frame_times:
            frame_times_ms = [t * 1000 for t in frame_times]  # Convert to milliseconds
            frame_times_ms.sort()
            frame_time_percentiles = {
                "p50": frame_times_ms[len(frame_times_ms) // 2],
                "p90": frame_times_ms[int(len(frame_times_ms) * 0.9)],
                "p95": frame_times_ms[int(len(frame_times_ms) * 0.95)],
                "p99": frame_times_ms[int(len(frame_times_ms) * 0.99)]
            }
        else:
            frame_time_percentiles = {"p50": 0, "p90": 0, "p95": 0, "p99": 0}
        
        # Calculate FPS stats only for complete seconds
        complete_seconds_fps = [s["frames"] for s in metrics["frames_per_second"]]
        
        # Calculate FPS percentiles (минимальный FPS, в который укладывается N% секунд)
        if complete_seconds_fps:
            complete_seconds_fps.sort(reverse=True)  # Сортируем по убыванию
            fps_percentiles = {
                "p50": complete_seconds_fps[len(complete_seconds_fps) // 2],  # 50% секунд имеют FPS не ниже этого значения
                "p75": complete_seconds_fps[int(len(complete_seconds_fps) * 0.75)],  # 75% секунд имеют FPS не ниже этого значения
                "p90": complete_seconds_fps[int(len(complete_seconds_fps) * 0.9)],  # 90% секунд имеют FPS не ниже этого значения
                "p95": complete_seconds_fps[int(len(complete_seconds_fps) * 0.95)],  # 95% секунд имеют FPS не ниже этого значения
                "p99": complete_seconds_fps[int(len(complete_seconds_fps) * 0.99)]   # 99% секунд имеют FPS не ниже этого значения
            }
        else:
            fps_percentiles = {"p50": 0, "p75": 0, "p90": 0, "p95": 0, "p99": 0}
        
        fps_stats = {
            "min_fps": min(complete_seconds_fps) if complete_seconds_fps else 0,
            "max_fps": max(complete_seconds_fps) if complete_seconds_fps else 0,
            "fps_stability": round(statistics.stdev(complete_seconds_fps), 2) if len(complete_seconds_fps) > 1 else 0,
            "percentiles": fps_percentiles
        }
        
        # Verify we have exactly 'duration' number of seconds
        if len(metrics["frames_per_second"]) != duration:
            self.logger.warning(
                "Expected %d seconds of data, but got %d seconds. Frames by second: %s", 
                duration, 
                len(metrics["frames_per_second"]),
                json.dumps(frames_by_second, indent=2)
            )
        
        metrics.update({
            "total_frames": frames_captured,
            "dropped_frames": failed_reads,  # Используем общее количество failed_reads
            "avg_fps": len(complete_seconds_fps) > 0 and sum(complete_seconds_fps) / len(complete_seconds_fps) or 0,
            "frame_time_min_ms": min(frame_times) * 1000 if frame_times else 0,
            "frame_time_max_ms": max(frame_times) * 1000 if frame_times else 0,
            "frame_time_percentiles_ms": frame_time_percentiles,
            "total_size_mb": file_size / (1024 * 1024),
            "bitrate_mbps": (file_size * 8) / (test_duration * 1024 * 1024) if test_duration > 0 else 0,
            "test_duration": test_duration,
            "analyzed_duration": duration,  # Duration of analyzed data (excluding incomplete seconds)
            "fps_stats": fps_stats
        })
        
        self.logger.info("Video capture completed. Metrics:")
        self.logger.info("  Connection time: %.2f seconds", metrics["connection_time"])
        self.logger.info("  Total frames: %d", metrics["total_frames"])
        self.logger.info("  Dropped frames: %d (%.1f%%)", 
                        metrics["dropped_frames"],
                        (metrics["dropped_frames"] / (metrics["total_frames"] + metrics["dropped_frames"]) * 100) if metrics["total_frames"] > 0 else 0)
        self.logger.info("  Average FPS: %.2f", metrics["avg_fps"])
        self.logger.info("  FPS range: %.1f-%.1f (stability: ±%.1f)", 
                        metrics["fps_stats"]["min_fps"],
                        metrics["fps_stats"]["max_fps"],
                        metrics["fps_stats"]["fps_stability"])
        self.logger.info("  FPS percentiles (minimum FPS for %% of time):")
        self.logger.info("    50%% of time: ≥%.1f fps", metrics["fps_stats"]["percentiles"]["p50"])
        self.logger.info("    75%% of time: ≥%.1f fps", metrics["fps_stats"]["percentiles"]["p75"])
        self.logger.info("    90%% of time: ≥%.1f fps", metrics["fps_stats"]["percentiles"]["p90"])
        self.logger.info("    95%% of time: ≥%.1f fps", metrics["fps_stats"]["percentiles"]["p95"])
        self.logger.info("    99%% of time: ≥%.1f fps", metrics["fps_stats"]["percentiles"]["p99"])
        self.logger.info("  Frame times - min: %.1fms, max: %.1fms", 
                        metrics["frame_time_min_ms"], 
                        metrics["frame_time_max_ms"])
        self.logger.info("  Frame time percentiles - p50: %.1fms, p90: %.1fms, p95: %.1fms, p99: %.1fms",
                        metrics["frame_time_percentiles_ms"]["p50"],
                        metrics["frame_time_percentiles_ms"]["p90"],
                        metrics["frame_time_percentiles_ms"]["p95"],
                        metrics["frame_time_percentiles_ms"]["p99"])
        self.logger.info("  Video size: %.2f MB", metrics["total_size_mb"])
        self.logger.info("  Bitrate: %.2f Mbps", metrics["bitrate_mbps"])
        self.logger.info("  Total test duration: %.2f seconds (analyzed %d seconds)", 
                        metrics["test_duration"], metrics["analyzed_duration"])
        
        return metrics

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

    def _generate_file_name(self, test_params: Dict[str, Any], file_type: str, extension: str) -> str:
        """Generate a standardized file name with all relevant parameters.
        
        Args:
            test_params: Test parameters
            file_type: Type of file (video/metrics/log)
            extension: File extension without dot
            
        Returns:
            Formatted file name with parameters
        """
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

    def _save_results(self, results: Dict[str, Any]) -> None:
        """Save test results to file.

        Args:
            results: Dictionary containing test results
        """
        metrics_dir = Path("results/metrics")
        metrics_dir.mkdir(parents=True, exist_ok=True)
        
        metrics_file = metrics_dir / self._generate_file_name(results["params"], "metrics", "json")
        
        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
            
        self.logger.info("Metrics saved to %s", metrics_file)

    def run_test_combination(self, test_params: Dict[str, Any], skip_build: bool = False) -> Dict[str, Any]:
        """Run a single test combination"""
        # Setup logging for this test
        log_file = Path("results/logs") / self._generate_file_name(test_params, "log", "log")
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        self.logger.addHandler(file_handler)
        
        test_start_time = time.time()
        self.logger.info("Starting test with parameters: %s", test_params)
        self.current_test_params = test_params
        results = {
            "params": test_params,
            "timestamp": datetime.now().isoformat(),
            "video_metrics": {},
            "control_metrics": {},
            "system_metrics": {
                "total_duration": 0,
                "build_time": 0,
                "flash_time": 0,
                "boot_time": 0
            },
            "errors": [],
        }

        try:
            if not skip_build:
                # Build firmware
                build_start = time.time()
                self.build_firmware(test_params)
                results["system_metrics"]["build_time"] = time.time() - build_start

                # Flash firmware
                self.logger.info("Flashing firmware to ESP32-CAM...")
                flash_start = time.time()
                flash_firmware(self.port)
                results["system_metrics"]["flash_time"] = time.time() - flash_start
            else:
                self.logger.info("Skipping firmware build and flash as requested")

            # Wait for device to boot and get IP
            self.logger.info("Waiting for device to boot and get IP...")
            boot_start = time.time()
            ip_address = wait_for_ip(self.port)
            if not ip_address:
                raise RuntimeError("Failed to get device IP address")
            results["system_metrics"]["boot_time"] = time.time() - boot_start
            self.logger.info("Device IP address: %s", ip_address)

            # Update config with actual IP and save it for video capture
            self.config["wifi"]["device_ip"] = ip_address

            # Wait additional time for all services to start
            time.sleep(self.config.get("warmup_time", 5))

            # Run video capture test if enabled
            if test_params.get("video_protocol"):
                video_path = (
                    Path("results/video") / self._generate_file_name(test_params, "video", "mp4")
                )
                video_path.parent.mkdir(parents=True, exist_ok=True)
                results["video_metrics"] = self.capture_video(self.config["test_duration"], str(video_path))
                results["video_metrics"]["path"] = str(video_path)

            # Run control test only if control protocol is specified
            if test_params.get("control_protocol"):
                self.logger.info("Starting control protocol test...")
                results["control_metrics"] = self.test_control(
                    self.config["test_duration"]
                )
            else:
                self.logger.info("Skipping control protocol test (not specified)")

            results["system_metrics"]["total_duration"] = time.time() - test_start_time
            self.logger.info("Test completed successfully in %.2f seconds", results["system_metrics"]["total_duration"])
            self.logger.info("System metrics:")
            if not skip_build:
                self.logger.info("  Build time: %.2f seconds", results["system_metrics"]["build_time"])
                self.logger.info("  Flash time: %.2f seconds", results["system_metrics"]["flash_time"])
            self.logger.info("  Boot time: %.2f seconds", results["system_metrics"]["boot_time"])

        except Exception as e:
            self.logger.error("Test failed: %s", str(e))
            results["errors"].append(str(e))
        finally:
            # Save metrics and clean up
            self._save_results(results)
            self.logger.removeHandler(file_handler)
            
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
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip firmware build and flash, only run tests",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    benchmark = ESPCamBenchmark()

    if args.single_test:
        if not all([args.video_protocol, args.resolution, args.quality]):
            print("Error: When running a single test, you must specify parameters:")
            print("  --video-protocol, --resolution, --quality")
            print("Optional parameters:")
            print("  --control-protocol, --metrics, --raw-mode, --duration, --skip-build")
            sys.exit(1)

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
        results = benchmark.run_test_combination(test_params, skip_build=args.skip_build)
        print(f"Test results: {json.dumps(results, indent=2)}")
    else:
        results = benchmark.run_all_tests()
