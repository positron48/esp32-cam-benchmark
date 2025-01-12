"""Command-line interface for ESP32-CAM benchmark."""

import argparse
import json
import sys

from . import ESPCamBenchmark


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
        "--quality", type=int, choices=range(3, 61), help="JPEG quality (1-61)"
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


def main():
    """Main entry point"""
    args = parse_args()
    benchmark = ESPCamBenchmark()

    if args.single_test:
        if not all([args.video_protocol, args.resolution, args.quality]):
            print("Error: When running a single test, you must specify parameters:")
            print("  --video-protocol, --resolution, --quality")
            print("Optional parameters:")
            print(
                "  --control-protocol, --metrics, --raw-mode, --duration, --skip-build"
            )
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
        results = benchmark.run_test_combination(
            test_params, skip_build=args.skip_build
        )
        print(f"Test results: {json.dumps(results, indent=2)}")
    else:
        results = benchmark.run_all_tests()


if __name__ == "__main__":
    main()