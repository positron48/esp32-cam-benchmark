#include <Arduino.h>
#include "esp_camera.h"
#include "esp_wifi.h"
#include <WiFi.h>
#include "config.h"
#include "camera.h"

// Protocol includes based on configuration
#if VIDEO_PROTOCOL == HTTP
#include "video_http.h"
#elif VIDEO_PROTOCOL == RTSP
#include "video_rtsp.h"
#elif VIDEO_PROTOCOL == UDP
#include "video_udp.h"
#elif VIDEO_PROTOCOL == WebRTC
#include "video_webrtc.h"
#endif

#if CONTROL_PROTOCOL == HTTP
#include "ctrl_http.h"
#elif CONTROL_PROTOCOL == UDP
#include "ctrl_udp.h"
#elif CONTROL_PROTOCOL == WebSocket
#include "ctrl_websocket.h"
#endif

// Task handles
TaskHandle_t videoTaskHandle = NULL;
TaskHandle_t controlTaskHandle = NULL;

// Video streaming task
void videoTask(void *parameter) {
    while (true) {
        #if VIDEO_PROTOCOL == HTTP
        handleVideoHTTP();
        #elif VIDEO_PROTOCOL == RTSP
        handleVideoRTSP();
        #elif VIDEO_PROTOCOL == UDP
        handleVideoUDP();
        #elif VIDEO_PROTOCOL == WebRTC
        handleVideoWebRTC();
        #endif
        vTaskDelay(1); // Small delay to prevent watchdog triggers
    }
}

// Control task
void controlTask(void *parameter) {
    while (true) {
        #if CONTROL_PROTOCOL == HTTP
        handleControlHTTP();
        #elif CONTROL_PROTOCOL == UDP
        handleControlUDP();
        #elif CONTROL_PROTOCOL == WebSocket
        handleControlWebSocket();
        #endif
        vTaskDelay(1); // Small delay to prevent watchdog triggers
    }
}

void setup() {
    #if ENABLE_METRICS
    Serial.begin(115200);
    #endif

    // Initialize camera
    if (!initCamera()) {
        #if ENABLE_METRICS
        Serial.println("Camera initialization failed");
        #endif
        return;
    }

    // Connect to WiFi
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        #if ENABLE_METRICS
        Serial.print(".");
        #endif
    }
    #if ENABLE_METRICS
    Serial.println("\nWiFi connected");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());
    #endif

    // Initialize protocols
    #if VIDEO_PROTOCOL == HTTP
    initVideoHTTP();
    #elif VIDEO_PROTOCOL == RTSP
    initVideoRTSP();
    #elif VIDEO_PROTOCOL == UDP
    initVideoUDP();
    #elif VIDEO_PROTOCOL == WebRTC
    initVideoWebRTC();
    #endif

    #if CONTROL_PROTOCOL == HTTP
    initControlHTTP();
    #elif CONTROL_PROTOCOL == UDP
    initControlUDP();
    #elif CONTROL_PROTOCOL == WebSocket
    initControlWebSocket();
    #endif

    // Create tasks on different cores
    xTaskCreatePinnedToCore(
        videoTask,
        "VideoTask",
        8192,
        NULL,
        1,
        &videoTaskHandle,
        0  // Core 0
    );

    xTaskCreatePinnedToCore(
        controlTask,
        "ControlTask",
        4096,
        NULL,
        1,
        &controlTaskHandle,
        1  // Core 1
    );
}

void loop() {
    // Main loop is empty as tasks handle everything
    vTaskDelay(1000);
} 