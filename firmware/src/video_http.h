#pragma once

#include <ESPAsyncWebServer.h>
#include <WiFi.h>

#include "config.h"
#include "esp_camera.h"

// Global web server instance
extern AsyncWebServer server;

// Initialize HTTP video streaming
void initVideoHTTP()
{
    server.on("/stream", HTTP_GET, [](AsyncWebServerRequest* request) {
        request->send(
            200,
            "text/html",
            "<html><body><img src='/video' style='width:100%;height:auto;'/></body></html>");
    });

    server.on("/video", HTTP_GET, [](AsyncWebServerRequest* request) {
        request->send(200, "multipart/x-mixed-replace; boundary=frame", "");
    });
}

// Handle HTTP video streaming
void handleVideoHTTP()
{
#if ENABLE_METRICS
    START_METRIC(frame_capture);
#endif

    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) {
#if ENABLE_METRICS
        Serial.println("Camera capture failed");
#endif
        return;
    }

#if ENABLE_METRICS
    END_METRIC(frame_capture);
    START_METRIC(frame_send);
#endif

    esp_camera_fb_return(fb);

#if ENABLE_METRICS
    END_METRIC(frame_send);
#endif

    // Small delay to maintain target frame rate
    vTaskDelay(pdMS_TO_TICKS(FRAME_INTERVAL_MS));
}
