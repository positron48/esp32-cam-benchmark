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

class AsyncMjpegStreamHandler: public AsyncWebHandler {
public:
    AsyncMjpegStreamHandler() {}
    virtual ~AsyncMjpegStreamHandler() {}

    bool canHandle(AsyncWebServerRequest *request) {
        return request->url() == "/video" && request->method() == HTTP_GET;
    }

    void handleRequest(AsyncWebServerRequest *request) {
        AsyncResponseStream *response = request->beginResponseStream(STREAM_CONTENT_TYPE);
        response->addHeader("Access-Control-Allow-Origin", "*");
        
        camera_fb_t *fb = esp_camera_fb_get();
        if (!fb) {
            request->send(500);
            return;
        }

        response->write(STREAM_BOUNDARY, strlen(STREAM_BOUNDARY));
        
        char buf[64];
        size_t len = snprintf(buf, sizeof(buf), STREAM_PART, fb->len);
        response->write(buf, len);
        response->write((char *)fb->buf, fb->len);
        
        esp_camera_fb_return(fb);
        request->send(response);
    }
};

// Initialize HTTP video streaming
void initVideoHTTP() {
    server.on("/stream", HTTP_GET, [](AsyncWebServerRequest* request) {
        AsyncWebServerResponse* response = request->beginResponse(
            200, 
            "text/html",
            "<html><head>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            "<style>img { width: 100%; height: auto; }</style>"
            "</head><body>"
            "<img src='/video' />"  // /video endpoint returns MJPEG stream which browser will automatically update
            "</body></html>"
        );
        response->addHeader("Access-Control-Allow-Origin", "*");
        request->send(response);
    });

    server.addHandler(new AsyncMjpegStreamHandler());
}

// Handle HTTP video streaming - now just maintains frame rate
void handleVideoHTTP() {
    // Small delay to maintain target frame rate
    vTaskDelay(pdMS_TO_TICKS(FRAME_INTERVAL_MS));
}
