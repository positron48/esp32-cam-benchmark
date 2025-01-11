"""Logging utilities for ESP32-CAM benchmark."""

import logging
import sys
from datetime import datetime
from pathlib import Path


def setup_logging() -> logging.Logger:
    """Setup logging configuration.
    
    Returns:
        Logger instance configured for the benchmark
    """
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