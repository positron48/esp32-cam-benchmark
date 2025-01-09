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
    key="$1"
    case $key in
        --video=*)
            VIDEO_PROTOCOL="${key#*=}"
            shift
            ;;
        --control=*)
            CONTROL_PROTOCOL="${key#*=}"
            shift
            ;;
        --resolution=*)
            CAMERA_RESOLUTION="${key#*=}"
            shift
            ;;
        --quality=*)
            JPEG_QUALITY="${key#*=}"
            shift
            ;;
        --metrics=*)
            ENABLE_METRICS="${key#*=}"
            shift
            ;;
        --raw=*)
            RAW_MODE="${key#*=}"
            shift
            ;;
        *)
            echo "Unknown parameter: $key"
            exit 1
            ;;
    esac
done

# Build the firmware with PlatformIO
export PLATFORMIO_BUILD_FLAGS="-DVIDEO_PROTOCOL=${VIDEO_PROTOCOL} -DCONTROL_PROTOCOL=${CONTROL_PROTOCOL} -DCAMERA_RESOLUTION=${CAMERA_RESOLUTION} -DJPEG_QUALITY=${JPEG_QUALITY} -DENABLE_METRICS=${ENABLE_METRICS} -DRAW_MODE=${RAW_MODE}"

.venv/bin/pio run --environment esp32cam

if [ $? -eq 0 ]; then
    echo "Build successful!"
    exit 0
else
    echo "Build failed!"
    exit 1
fi 