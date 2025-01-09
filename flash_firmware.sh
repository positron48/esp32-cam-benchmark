#!/bin/bash

# Default port
PORT="/dev/ttyUSB0"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        --port=*)
            PORT="${key#*=}"
            shift
            ;;
        *)
            echo "Unknown parameter: $key"
            exit 1
            ;;
    esac
done

# Check if port exists
if [ ! -e "$PORT" ]; then
    echo "Error: Port $PORT does not exist!"
    exit 1
fi

# Flash the firmware
echo "Flashing firmware to $PORT..."
.venv/bin/pio run -t upload --upload-port $PORT

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "Flash successful!"
    exit 0
else
    echo "Flash failed!"
    exit 1
fi 