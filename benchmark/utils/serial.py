"""Serial port utilities for ESP32-CAM benchmark."""

import logging
import re
import subprocess
import time
from typing import Optional

import serial
import serial.tools.list_ports


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
        "USB2Serial": "USB-Serial",
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