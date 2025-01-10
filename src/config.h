#pragma once

// WiFi credentials
#define WIFI_SSID "your_ssid"
#define WIFI_PASS "your_password"

// Camera pins for ESP32-CAM
#define PWDN_GPIO_NUM  32
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM  0
#define SIOD_GPIO_NUM  26
#define SIOC_GPIO_NUM  27
#define Y9_GPIO_NUM    35
#define Y8_GPIO_NUM    34
#define Y7_GPIO_NUM    39
#define Y6_GPIO_NUM    36
#define Y5_GPIO_NUM    21
#define Y4_GPIO_NUM    19
#define Y3_GPIO_NUM    18
#define Y2_GPIO_NUM    5
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM  23
#define PCLK_GPIO_NUM  22

// Frame interval in milliseconds (1000/FPS)
#define FRAME_INTERVAL_MS 100  // 10 FPS

// Metrics
#if ENABLE_METRICS
#define START_METRIC(name) uint32_t name##_start = millis()
#define END_METRIC(name)                                                             \
    do {                                                                             \
        uint32_t name##_end      = millis();                                         \
        uint32_t name##_duration = static_cast<uint32_t>(name##_end - name##_start); \
        Serial.printf("%s: %u ms\n", #name, name##_duration);                        \
    } while (0)
#else
#define START_METRIC(name)
#define END_METRIC(name)
#endif
