#pragma once

// WiFi credentials - these will be overridden by build flags
#ifndef WIFI_SSID
#define WIFI_SSID "your_wifi_ssid"
#endif

#ifndef WIFI_PASSWORD
#define WIFI_PASSWORD "your_wifi_password"
#endif

// Video protocol selection
#ifndef VIDEO_PROTOCOL
#define VIDEO_PROTOCOL HTTP
#endif

// Control protocol selection
#ifndef CONTROL_PROTOCOL
#define CONTROL_PROTOCOL HTTP
#endif

// Camera settings
#ifndef CAMERA_RESOLUTION
#define CAMERA_RESOLUTION VGA
#endif

#ifndef JPEG_QUALITY
#define JPEG_QUALITY 10
#endif

// Raw mode vs JPEG
#ifndef RAW_MODE
#define RAW_MODE 0
#endif

// Metrics/monitoring
#ifndef ENABLE_METRICS
#define ENABLE_METRICS 1
#endif

// Resolution definitions
#define RESOLUTION_QQVGA   {160, 120}
#define RESOLUTION_QVGA    {320, 240}
#define RESOLUTION_VGA     {640, 480}
#define RESOLUTION_SVGA    {800, 600}
#define RESOLUTION_XGA     {1024, 768}
#define RESOLUTION_SXGA    {1280, 1024}
#define RESOLUTION_UXGA    {1600, 1200}

// Network ports
#define HTTP_PORT 80
#define RTSP_PORT 8554
#define UDP_VIDEO_PORT 5000
#define UDP_CONTROL_PORT 5001
#define WEBSOCKET_PORT 81

// Buffer sizes
#define FRAME_BUFFER_SIZE (1024 * 1024)  // 1MB frame buffer
#define CONTROL_BUFFER_SIZE 256

// Task priorities
#define VIDEO_TASK_PRIORITY 1
#define CONTROL_TASK_PRIORITY 1

// Task stack sizes
#define VIDEO_TASK_STACK_SIZE 8192
#define CONTROL_TASK_STACK_SIZE 4096

// Timing parameters
#define FRAME_INTERVAL_MS 33  // ~30 FPS
#define CONTROL_INTERVAL_MS 10

// Metrics
#if ENABLE_METRICS
#define START_METRIC(name) unsigned long metric_##name = millis()
#define END_METRIC(name) do { \
    unsigned long duration = millis() - metric_##name; \
    Serial.printf("%s: %lu ms\n", #name, duration); \
} while(0)
#else
#define START_METRIC(name)
#define END_METRIC(name)
#endif 