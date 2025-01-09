#pragma once

#include <ArduinoJson.h>
#include <ESPAsyncWebServer.h>
#include "camera.h"

void initControlHTTP() {
    server.on("/control", HTTP_POST, [](AsyncWebServerRequest *request) {
        request->send(200);
    }, nullptr, [](AsyncWebServerRequest *request, uint8_t *data, size_t len, size_t index, size_t total) {
        JsonDocument doc;
        DeserializationError error = deserializeJson(doc, (const char*)data, len);
        if (error) {
            request->send(400, "text/plain", "Invalid JSON");
            return;
        }

        if (doc["pan"].is<int>()) {
            camera_pan(doc["pan"].as<int>());
        }
        if (doc["tilt"].is<int>()) {
            camera_tilt(doc["tilt"].as<int>());
        }
        if (doc["zoom"].is<int>()) {
            camera_zoom(doc["zoom"].as<int>());
        }
        if (doc["led"].is<int>()) {
            camera_led(doc["led"].as<int>());
        }
        if (doc["brightness"].is<int>()) {
            camera_brightness(doc["brightness"].as<int>());
        }
    });

    server.on("/status", HTTP_GET, [](AsyncWebServerRequest *request) {
        JsonDocument doc;
        doc["pan"] = camera_get_pan();
        doc["tilt"] = camera_get_tilt();
        doc["zoom"] = camera_get_zoom();
        doc["led"] = camera_get_led();
        doc["brightness"] = camera_get_brightness();

        String response;
        serializeJson(doc, response);
        request->send(200, "application/json", response);
    });
}
