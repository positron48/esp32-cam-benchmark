#pragma once

#include <ArduinoJson.h>
#include <WebSocketsServer.h>

#include "config.h"

// WebSocket server instance
WebSocketsServer webSocket(WEBSOCKET_PORT);

// Control command structure (shared with other protocols)
struct ControlCommand {
    int  pan;         // -100 to 100
    int  tilt;        // -100 to 100
    int  zoom;        // -100 to 100
    bool led;         // true/false
    int  brightness;  // 0 to 100
};

// Current control state
static ControlCommand currentControl = {0, 0, 0, false, 50};

// WebSocket event handler
void webSocketEvent(uint8_t num, WStype_t type, uint8_t* payload, size_t length) {
    switch (type) {
        case WStype_DISCONNECTED:
#if ENABLE_METRICS
            Serial.printf("[%u] Disconnected!\n", num);
#endif
            break;

        case WStype_CONNECTED: {
#if ENABLE_METRICS
            Serial.printf("[%u] Connected!\n", num);
#endif

            // Send current state on connection
            StaticJsonDocument<200> doc;
            doc["pan"]        = currentControl.pan;
            doc["tilt"]       = currentControl.tilt;
            doc["zoom"]       = currentControl.zoom;
            doc["led"]        = currentControl.led;
            doc["brightness"] = currentControl.brightness;

            String response;
            serializeJson(doc, response);
            webSocket.sendTXT(num, response);
        } break;

        case WStype_TEXT: {
#if ENABLE_METRICS
            START_METRIC(control_process);
#endif

            StaticJsonDocument<200> doc;
            DeserializationError    error = deserializeJson(doc, payload, length);

            if (!error) {
                if (doc.containsKey("pan"))
                    currentControl.pan = doc["pan"];
                if (doc.containsKey("tilt"))
                    currentControl.tilt = doc["tilt"];
                if (doc.containsKey("zoom"))
                    currentControl.zoom = doc["zoom"];
                if (doc.containsKey("led"))
                    currentControl.led = doc["led"];
                if (doc.containsKey("brightness"))
                    currentControl.brightness = doc["brightness"];

#if ENABLE_METRICS
                Serial.printf(
                    "Control update - Pan: %d, Tilt: %d, Zoom: %d, LED: %d, Brightness: %d\n",
                    currentControl.pan,
                    currentControl.tilt,
                    currentControl.zoom,
                    currentControl.led,
                    currentControl.brightness);
#endif

                // Send acknowledgment
                StaticJsonDocument<200> response;
                response["status"]   = "ok";
                response["received"] = true;

                String responseStr;
                serializeJson(response, responseStr);
                webSocket.sendTXT(num, responseStr);
            }

#if ENABLE_METRICS
            END_METRIC(control_process);
#endif
        } break;
    }
}

// Initialize WebSocket control server
void initControlWebSocket() {
    webSocket.begin();
    webSocket.onEvent(webSocketEvent);

#if ENABLE_METRICS
    Serial.printf("WebSocket server started on port %d\n", WEBSOCKET_PORT);
#endif
}

// Handle WebSocket control updates
void handleControlWebSocket() {
    // Handle WebSocket events
    webSocket.loop();

// Apply control values to hardware
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
