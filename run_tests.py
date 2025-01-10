#!/usr/bin/env python3

import yaml
import subprocess
import time
import os
import json
from typing import Dict, Any, List
import cv2  # type: ignore
import numpy as np
from datetime import datetime
from pathlib import Path


class ESPCamBenchmark:
    def __init__(self, config_file="bench_config.yml"):
        with open(config_file, "r") as f:
            self.config = yaml.safe_load(f)

    def build_firmware(self, params: Dict[str, Any], dry_run: bool = False) -> List[str]:
        """Build firmware with specified parameters
        
        Args:
            params: Dictionary with build parameters
            dry_run: If True, only return the command without executing it
        
        Returns:
            List of command arguments
        """
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
            return cmd

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            return cmd
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Build failed: {e.stdout}") from e

    def capture_video(self, duration: int, output_path: str) -> None:
        """Capture video stream for specified duration"""
        cap = cv2.VideoCapture(0)  # type: ignore
        if not cap.isOpened():
            raise RuntimeError("Failed to open camera")

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))  # type: ignore
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))  # type: ignore
        fps = 30

        out = cv2.VideoWriter(  # type: ignore
            output_path,
            cv2.VideoWriter_fourcc(*"mp4v"),  # type: ignore
            fps,
            (width, height),
        )

        start_time = time.time()
        while (time.time() - start_time) < duration:
            ret, frame = cap.read()
            if ret:
                out.write(frame)

        cap.release()
        out.release()

    def test_control(self, duration: int) -> Dict[str, Any]:
        """Test control commands"""
        results = {"latency": [], "success_rate": 0, "errors": []}

        start_time = time.time()
        while (time.time() - start_time) < duration:
            try:
                # Send test commands and measure response time
                cmd_start = time.time()
                # TODO: Implement actual control command testing
                cmd_end = time.time()
                results["latency"].append(cmd_end - cmd_start)
            except Exception as e:
                results["errors"].append(str(e))

        total_commands = len(results["latency"]) + len(results["errors"])
        if total_commands > 0:
            results["success_rate"] = len(results["latency"]) / total_commands

        return results

    def run_test_combination(
            self, test_params: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test combination"""
        results = {
            "params": test_params,
            "timestamp": datetime.now().isoformat(),
            "video_metrics": {},
            "control_metrics": {},
            "errors": [],
        }

        try:
            # Build and flash firmware
            self.build_firmware(test_params)
            time.sleep(5)  # Wait for device to boot

            # Run video capture test if enabled
            if test_params.get("video_protocol"):
                video_path = f"results/video/{test_params['video_protocol']}_{test_params['resolution']}_{test_params['quality']}.mp4"
                self.capture_video(self.config["test_duration"], video_path)

            # Run control test if enabled
            if test_params.get("control_protocol"):
                results["control_metrics"] = self.test_control(
                    self.config["test_duration"]
                )

        except Exception as e:
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
                                            results = self.run_test_combination(
                                                params)
                                            all_results.append(results)

                                            # Save results after each test
                                            self._save_results(results)

        except Exception as e:
            print(f"Error running tests: {e}")

        return all_results

    def _save_results(self, results: Dict[str, Any]) -> None:
        """Save test results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = f"results/logs/test_{timestamp}.json"

        with open(result_file, "w") as f:
            json.dump(results, f, indent=2)


if __name__ == "__main__":
    benchmark = ESPCamBenchmark()
    results = benchmark.run_all_tests()
