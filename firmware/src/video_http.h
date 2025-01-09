#pragma once

#include <ESPAsyncWebServer.h>
#include "esp_camera.h"
#include "config.h"

// Global web server instance
extern AsyncWebServer webServer;

// Initialize HTTP video streaming
void initVideoHTTP() {
    webServer.on("/stream", HTTP_GET, [](AsyncWebServerRequest *request){
        request->send_P(200, "text/html", 
            "<html><body><img src='/video' style='width:100%;height:auto;'/></body></html>");
    });

    webServer.on("/video", HTTP_GET, [](AsyncWebServerRequest *request){
        request->send(200, "multipart/x-mixed-replace; boundary=frame", "");
    }, NULL, [](AsyncWebServerRequest *request, uint8_t *data, size_t len, size_t index, size_t total){
        if(!index) {
            request->_tempObject = (void*)new bool(true);
        }
    });

    webServer.begin();
}

// Handle HTTP video streaming
void handleVideoHTTP() {
    #if ENABLE_METRICS
    START_METRIC(frame_capture);
    #endif

    camera_fb_t *fb = esp_camera_fb_get();
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

    static const char* STREAM_CONTENT = "--frame\r\n"
                                      "Content-Type: image/%s\r\n"
                                      "Content-Length: %u\r\n\r\n";

    char *part_buf[128];
    sprintf((char*)part_buf, STREAM_CONTENT, RAW_MODE ? "raw" : "jpeg", fb->len);

    webServer.on("/video", HTTP_GET, [fb, part_buf](AsyncWebServerRequest *request){
        AsyncWebServerResponse *response = request->beginResponse(
            200, "multipart/x-mixed-replace; boundary=frame", "");
        response->print((char*)part_buf);
        response->write(fb->buf, fb->len);
        response->print("\r\n");
        request->send(response);
    });

    #if ENABLE_METRICS
    END_METRIC(frame_send);
    #endif

    esp_camera_fb_return(fb);

    // Small delay to maintain target frame rate
    vTaskDelay(pdMS_TO_TICKS(FRAME_INTERVAL_MS));
} 