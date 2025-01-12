#include <Arduino.h>
#include <ESPAsyncWebServer.h>
#include <WiFi.h>

#include "camera.h"
#include "config.h"
#include "ctrl_http.h"
#include "esp_camera.h"
#include "video_http.h"

// Global web server instance
AsyncWebServer server(80);

void setup() {
    Serial.begin(115200);
    delay(1000);  // Wait for serial to stabilize
    Serial.println("\n=== ESP32-CAM Initialization ===");

// Convert defines to strings for better logging
#define XSTR(x)  STR(x)
#define STR(x)  #x

#define _CONCAT(a, b) a##b
#define CONCAT(a, b) _CONCAT(a, b)

    Serial.printf("- Video Protocol: %s\n", XSTR(VIDEO_PROTOCOL));
    Serial.printf("- Control Protocol: %s\n", XSTR(CONTROL_PROTOCOL));
    Serial.printf("- Camera Resolution: %s\n", XSTR(CAMERA_RESOLUTION));
    Serial.printf("- JPEG Quality: %d\n", JPEG_QUALITY);
    Serial.printf("- Metrics Enabled: %d\n", ENABLE_METRICS);
    Serial.printf("- Raw Mode: %d\n\n", RAW_MODE);

    Serial.println("Initializing camera...");
    // Initialize camera hardware
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer   = LEDC_TIMER_0;
    config.pin_d0       = Y2_GPIO_NUM;
    config.pin_d1       = Y3_GPIO_NUM;
    config.pin_d2       = Y4_GPIO_NUM;
    config.pin_d3       = Y5_GPIO_NUM;
    config.pin_d4       = Y6_GPIO_NUM;
    config.pin_d5       = Y7_GPIO_NUM;
    config.pin_d6       = Y8_GPIO_NUM;
    config.pin_d7       = Y9_GPIO_NUM;
    config.pin_xclk     = XCLK_GPIO_NUM;
    config.pin_pclk     = PCLK_GPIO_NUM;
    config.pin_vsync    = VSYNC_GPIO_NUM;
    config.pin_href     = HREF_GPIO_NUM;
    config.pin_sscb_sda = SIOD_GPIO_NUM;
    config.pin_sscb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn     = PWDN_GPIO_NUM;
    config.pin_reset    = RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;
    config.frame_size   = CONCAT(FRAMESIZE_, CAMERA_RESOLUTION);
    config.jpeg_quality = JPEG_QUALITY;
    config.fb_count     = 2;

    Serial.println("Camera configuration:");
    Serial.printf("- XCLK Frequency: %d Hz\n", config.xclk_freq_hz);
    Serial.printf("- Frame Size: %d\n", config.frame_size);
    Serial.printf("- JPEG Quality: %d\n", config.jpeg_quality);
    Serial.printf("- FB Count: %d\n", config.fb_count);

    // Initialize the camera
    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("Camera initialization failed with error 0x%x\n", err);
        return;
    }
    Serial.println("Camera initialized successfully!");

    // Initialize camera control
    Serial.println("Initializing camera control...");
    camera_init();
    Serial.println("Camera control initialized!");

    // Connect to WiFi
    Serial.printf("\nConnecting to WiFi network: %s\n", WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
        attempts++;
        if (attempts % 20 == 0) {
            Serial.printf("\nStill trying to connect (attempt %d)...\n", attempts);
        }
    }
    Serial.println("\nWiFi connected!");
    Serial.printf("- SSID: %s\n", WIFI_SSID);
    Serial.printf("- IP address: %s\n", WiFi.localIP().toString().c_str());
    Serial.printf("- Signal strength: %d dBm\n", WiFi.RSSI());

    // Initialize HTTP server
    Serial.println("\nInitializing HTTP server...");
    initVideoHTTP();
    initControlHTTP();
    server.begin();
    Serial.println("HTTP server started!");

    Serial.println("\n=== Initialization Complete ===");
    Serial.printf("Camera Ready! Use 'http://%s' to connect\n", WiFi.localIP().toString().c_str());
}

void loop() {
    static uint32_t lastLog = 0;
    handleVideoHTTP();

    // Log status every 10 seconds
    if (millis() - lastLog > 10000) {
        Serial.printf(
            "Status: WiFi RSSI=%d dBm, Free heap=%d bytes\n", WiFi.RSSI(), ESP.getFreeHeap());
        lastLog = millis();
    }
}
