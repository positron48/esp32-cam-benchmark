#!/bin/bash

# Default values
VIDEO_PROTOCOL="HTTP"
CONTROL_PROTOCOL="HTTP"
CAMERA_RESOLUTION="VGA"
JPEG_QUALITY=10
ENABLE_METRICS=1
RAW_MODE=0

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --video)
            VIDEO_PROTOCOL="$2"
            shift 2
            ;;
        --control)
            CONTROL_PROTOCOL="$2"
            shift 2
            ;;
        --resolution)
            CAMERA_RESOLUTION="$2"
            shift 2
            ;;
        --quality)
            JPEG_QUALITY="$2"
            shift 2
            ;;
        --metrics)
            ENABLE_METRICS="$2"
            shift 2
            ;;
        --raw)
            RAW_MODE="$2"
            shift 2
            ;;
        *)
            echo "Unknown parameter: $1"
            exit 1
            ;;
    esac
done

# Build the firmware with PlatformIO
pio run \
    -e esp32cam \
    --build-flags "\
    -D VIDEO_PROTOCOL=${VIDEO_PROTOCOL} \
    -D CONTROL_PROTOCOL=${CONTROL_PROTOCOL} \
    -D CAMERA_RESOLUTION=${CAMERA_RESOLUTION} \
    -D JPEG_QUALITY=${JPEG_QUALITY} \
    -D ENABLE_METRICS=${ENABLE_METRICS} \
    -D RAW_MODE=${RAW_MODE}"

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "Build successful!"
    exit 0
else
    echo "Build failed!"
    exit 1
fi 