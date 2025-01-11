#pragma once

#include <ESPAsyncWebServer.h>
#include <WiFi.h>

#include "config.h"
#include "esp_camera.h"

#define BOUNDARY "123456789000000000000987654321"
#define STREAM_CONTENT_TYPE "multipart/x-mixed-replace;boundary=" BOUNDARY
#define STREAM_BOUNDARY "\r\n--" BOUNDARY "\r\n"
#define STREAM_PART "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n"

// Global web server instance
extern AsyncWebServer server;

// Initialize HTTP video streaming
void initVideoHTTP() {
    server.on("/stream", HTTP_GET, [](AsyncWebServerRequest* request) {
        AsyncWebServerResponse* response = request->beginResponse(
            200, 
            "text/html",
            "<html><body><img src='/video' style='width:100%;height:auto;'/></body></html>"
        );
        response->addHeader("Access-Control-Allow-Origin", "*");
        request->send(response);
    });

    server.on(
        "/video",
        HTTP_GET,
        [](AsyncWebServerRequest* request) {
            static char* part_buf = (char*)malloc(64);
            static char* boundary = (char*)malloc(strlen(STREAM_BOUNDARY) + 1);
            if (!part_buf || !boundary) {
                request->send(500);
                return;
            }
            
            camera_fb_t* fb = esp_camera_fb_get();
            if (!fb) {
                request->send(500);
                return;
            }

            AsyncResponseStream* response = request->beginResponseStream(STREAM_CONTENT_TYPE);
            response->addHeader("Access-Control-Allow-Origin", "*");
            
            strcpy(boundary, STREAM_BOUNDARY);
            response->write(boundary, strlen(boundary));
            
            sprintf(part_buf, STREAM_PART, fb->len);
            response->write(part_buf, strlen(part_buf));
            response->write((char*)fb->buf, fb->len);
            
            esp_camera_fb_return(fb);
            request->send(response);
        },
        NULL
    );
}

// Handle HTTP video streaming - now just maintains frame rate
void handleVideoHTTP() {
    // Small delay to maintain target frame rate
    vTaskDelay(pdMS_TO_TICKS(FRAME_INTERVAL_MS));
}
