"""Control protocol functionality for ESP32-CAM benchmark."""

import statistics
import time
from typing import Any, Dict

import requests


def test_control(
    ip_address: str, protocol: str, duration: int, logger: Any
) -> Dict[str, Any]:
    """Test control commands.

    Args:
        ip_address: Device IP address
        protocol: Control protocol to test
        duration: Duration of test in seconds
        logger: Logger instance

    Returns:
        Dictionary with test results
    """
    logger.info("Starting control protocol test: protocol=%s", protocol)
    metrics = {
        "latency": [],
        "success_rate": 0,
        "errors": [],
        "commands_per_second": [],
        "latency_stats": {
            "min_ms": 0,
            "max_ms": 0,
            "avg_ms": 0,
            "stability_ms": 0,
            "percentiles": {
                "p50": 0,
                "p90": 0,
                "p95": 0,
                "p99": 0,
            },
        },
    }

    # Test parameters
    test_commands = [
        {"pan": 0},
        {"pan": 90},
        {"pan": -90},
        {"tilt": 0},
        {"tilt": 45},
        {"tilt": -45},
        {"zoom": 1},
        {"zoom": 2},
        {"zoom": 4},
    ]

    # Construct control URL based on protocol
    if protocol == "HTTP":
        url = f"http://{ip_address}/control"

        def send_command(cmd):
            return _send_http_command(url, cmd)

    elif protocol == "UDP":
        url = f"udp://{ip_address}:5001"

        def send_command(cmd):
            return _send_udp_command(url, cmd)

    elif protocol == "WebSocket":
        url = f"ws://{ip_address}:8080/control"

        def send_command(cmd):
            return _send_ws_command(url, cmd)

    else:
        raise ValueError(f"Unsupported control protocol: {protocol}")

    # Run test
    commands_sent = 0
    start_time = time.time()
    current_second = 0
    commands_this_second = 0

    while (time.time() - start_time) < duration:
        for cmd in test_commands:
            try:
                # Send command and measure response time
                cmd_start = time.time()
                send_command(cmd)
                cmd_end = time.time()

                # Calculate metrics
                latency = (cmd_end - cmd_start) * 1000  # Convert to ms
                metrics["latency"].append(latency)
                commands_sent += 1

                # Track commands per second
                second = int(time.time() - start_time)
                if second > current_second:
                    if current_second > 0:  # Skip first incomplete second
                        metrics["commands_per_second"].append(
                            {
                                "second": current_second,
                                "commands": commands_this_second,
                                "errors": 0,
                            }
                        )
                    current_second = second
                    commands_this_second = 0
                commands_this_second += 1

                # Log progress
                if commands_sent % 10 == 0:
                    logger.debug(
                        "Sent %d commands, last latency: %.3f ms",
                        commands_sent,
                        latency,
                    )

            except Exception as e:
                logger.error("Control command failed: %s", str(e))
                metrics["errors"].append(str(e))
                # Track error in current second
                if current_second > 0:
                    metrics["commands_per_second"][-1]["errors"] += 1

    # Calculate final metrics
    total_commands = len(metrics["latency"]) + len(metrics["errors"])
    if total_commands > 0:
        metrics["success_rate"] = len(metrics["latency"]) / total_commands

    if metrics["latency"]:
        latencies = sorted(metrics["latency"])
        metrics["latency_stats"].update(
            {
                "min_ms": min(latencies),
                "max_ms": max(latencies),
                "avg_ms": sum(latencies) / len(latencies),
                "stability_ms": statistics.stdev(latencies)
                if len(latencies) > 1
                else 0,
                "percentiles": {
                    "p50": latencies[len(latencies) // 2],
                    "p90": latencies[int(len(latencies) * 0.9)],
                    "p95": latencies[int(len(latencies) * 0.95)],
                    "p99": latencies[int(len(latencies) * 0.99)],
                },
            }
        )

    # Log results
    _log_control_metrics(metrics, logger)
    return metrics


def _send_http_command(url: str, command: Dict[str, Any]) -> Dict[str, Any]:
    """Send command via HTTP.

    Args:
        url: Control endpoint URL
        command: Command to send

    Returns:
        Response data
    """
    response = requests.post(url, json=command, timeout=5.0)
    response.raise_for_status()
    return response.json()


def _send_udp_command(url: str, command: Dict[str, Any]) -> Dict[str, Any]:
    """Send command via UDP.

    Args:
        url: Control endpoint URL
        command: Command to send

    Returns:
        Response data
    """
    # TODO: Implement UDP command sending
    raise NotImplementedError("UDP control not implemented yet")


def _send_ws_command(url: str, command: Dict[str, Any]) -> Dict[str, Any]:
    """Send command via WebSocket.

    Args:
        url: Control endpoint URL
        command: Command to send

    Returns:
        Response data
    """
    # TODO: Implement WebSocket command sending
    raise NotImplementedError("WebSocket control not implemented yet")


def _log_control_metrics(metrics: Dict[str, Any], logger: Any) -> None:
    """Log control test metrics.

    Args:
        metrics: Dictionary with metrics
        logger: Logger instance
    """
    logger.info("Control test completed. Metrics:")
    logger.info(
        "  Success rate: %.1f%% (%d/%d commands)",
        metrics["success_rate"] * 100,
        len(metrics["latency"]),
        len(metrics["latency"]) + len(metrics["errors"]),
    )
    if metrics["latency"]:
        logger.info(
            "  Latency - min: %.1fms, max: %.1fms, avg: %.1fms (±%.1fms)",
            metrics["latency_stats"]["min_ms"],
            metrics["latency_stats"]["max_ms"],
            metrics["latency_stats"]["avg_ms"],
            metrics["latency_stats"]["stability_ms"],
        )
        logger.info("  Latency percentiles:")
        logger.info("    50%%: %.1fms", metrics["latency_stats"]["percentiles"]["p50"])
        logger.info("    90%%: %.1fms", metrics["latency_stats"]["percentiles"]["p90"])
        logger.info("    95%%: %.1fms", metrics["latency_stats"]["percentiles"]["p95"])
        logger.info("    99%%: %.1fms", metrics["latency_stats"]["percentiles"]["p99"])

    if metrics["errors"]:
        logger.info("  Errors encountered:")
        for error in metrics["errors"]:
            logger.info("    - %s", error)

    logger.info("  Commands per second:")
    for second in metrics["commands_per_second"]:
        logger.info(
            "    Second %d: %d commands (%d errors)",
            second["second"],
            second["commands"],
            second["errors"],
        )
