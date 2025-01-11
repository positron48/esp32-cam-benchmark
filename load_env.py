Import("env")
import os
from pathlib import Path

# Load .env file
env_path = Path(".") / ".env"
if env_path.exists():
    print("Loading environment from .env file")
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                key, value = line.split("=", 1)
                # Remove quotes if present
                value = value.strip("\"'")
                os.environ[key.strip()] = value

# Add WiFi credentials to build flags
wifi_ssid = os.getenv("WIFI_SSID", "your_ssid")
wifi_pass = os.getenv("WIFI_PASSWORD", "your_password")

env.Append(
    BUILD_FLAGS=[f'-DWIFI_SSID=\\"{wifi_ssid}\\"', f'-DWIFI_PASS=\\"{wifi_pass}\\"']
)
