#pragma once

#include <ArduinoJson.h>
#include <WiFi.h>
#include <WiFiUdp.h>

#include "config.h"

// UDP instance for control commands
WiFiUDP controlUDP;

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

// Buffer for incoming packets
char packetBuffer[CONTROL_BUFFER_SIZE];

// Initialize UDP control server
void initControlUDP() {
    controlUDP.begin(UDP_CONTROL_PORT);
}

// Process incoming UDP control packet
void processControlPacket(char* data, size_t len) {
#if ENABLE_METRICS
    START_METRIC(control_process);
#endif

    StaticJsonDocument<200> doc;
    DeserializationError    error = deserializeJson(doc, data, len);

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
        Serial.printf("Control update - Pan: %d, Tilt: %d, Zoom: %d, LED: %d, Brightness: %d\n",
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

        controlUDP.beginPacket(controlUDP.remoteIP(), controlUDP.remotePort());
        controlUDP.print(responseStr);
        controlUDP.endPacket();
    }

#if ENABLE_METRICS
    END_METRIC(control_process);
#endif
}

// Handle UDP control commands
void handleControlUDP() {
    // Check for incoming packets
    int packetSize = controlUDP.parsePacket();
    if (packetSize) {
#if ENABLE_METRICS
        Serial.printf("Received UDP packet of size %d from %s:%d\n",
                      packetSize,
                      controlUDP.remoteIP().toString().c_str(),
                      controlUDP.remotePort());
#endif

        // Read the packet
        int len = controlUDP.read(packetBuffer, CONTROL_BUFFER_SIZE - 1);
        if (len > 0) {
            packetBuffer[len] = 0;  // Null terminate
            processControlPacket(packetBuffer, len);
        }
    }

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
