#!/bin/bash

# Default port
PORT="/dev/ttyUSB0"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT="$2"
            shift 2
            ;;
        *)
            echo "Unknown parameter: $1"
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
pio run -t upload --upload-port $PORT

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "Flash successful!"
    # Wait for device to reset
    sleep 2
    # Start serial monitor
    if [ "$MONITOR" = "true" ]; then
        pio device monitor --port $PORT
    fi
    exit 0
else
    echo "Flash failed!"
    exit 1
fi 