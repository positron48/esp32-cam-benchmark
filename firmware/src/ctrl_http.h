#pragma once

#include <ESPAsyncWebServer.h>
#include <ArduinoJson.h>
#include "config.h"

// Global web server instance (shared with video_http)
AsyncWebServer webServer(HTTP_PORT);

// Control command structure
struct ControlCommand {
    int pan;        // -100 to 100
    int tilt;       // -100 to 100
    int zoom;       // -100 to 100
    bool led;       // true/false
    int brightness; // 0 to 100
};

// Current control state
static ControlCommand currentControl = {0, 0, 0, false, 50};

// Initialize HTTP control server
void initControlHTTP() {
    // Handle control commands via POST
    webServer.on("/control", HTTP_POST, [](AsyncWebServerRequest *request){
        request->send(200);
    }, NULL, [](AsyncWebServerRequest *request, uint8_t *data, size_t len){
        #if ENABLE_METRICS
        START_METRIC(control_process);
        #endif

        StaticJsonDocument<200> doc;
        DeserializationError error = deserializeJson(doc, data, len);
        
        if (!error) {
            if (doc.containsKey("pan")) currentControl.pan = doc["pan"];
            if (doc.containsKey("tilt")) currentControl.tilt = doc["tilt"];
            if (doc.containsKey("zoom")) currentControl.zoom = doc["zoom"];
            if (doc.containsKey("led")) currentControl.led = doc["led"];
            if (doc.containsKey("brightness")) currentControl.brightness = doc["brightness"];
            
            #if ENABLE_METRICS
            Serial.printf("Control update - Pan: %d, Tilt: %d, Zoom: %d, LED: %d, Brightness: %d\n",
                currentControl.pan, currentControl.tilt, currentControl.zoom, 
                currentControl.led, currentControl.brightness);
            #endif
        }
        
        #if ENABLE_METRICS
        END_METRIC(control_process);
        #endif
    });

    // Handle control state query via GET
    webServer.on("/control", HTTP_GET, [](AsyncWebServerRequest *request){
        StaticJsonDocument<200> doc;
        doc["pan"] = currentControl.pan;
        doc["tilt"] = currentControl.tilt;
        doc["zoom"] = currentControl.zoom;
        doc["led"] = currentControl.led;
        doc["brightness"] = currentControl.brightness;
        
        String response;
        serializeJson(doc, response);
        request->send(200, "application/json", response);
    });
}

// Handle control updates
void handleControlHTTP() {
    // Apply control values to hardware
    // This would be implemented based on your specific hardware setup
    // For example, controlling servos for pan/tilt, LED brightness, etc.
    
    #if ENABLE_METRICS
    START_METRIC(control_apply);
    #endif

    // Example LED control using built-in LED
    #ifdef LED_BUILTIN
    if (currentControl.led) {
        digitalWrite(LED_BUILTIN, HIGH);
    } else {
        digitalWrite(LED_BUILTIN, LOW);
    }
    #endif

    #if ENABLE_METRICS
    END_METRIC(control_apply);
    #endif

    // Small delay to prevent too frequent updates
    vTaskDelay(pdMS_TO_TICKS(CONTROL_INTERVAL_MS));
} 