#pragma once

#include <ArduinoJson.h>
#include <WebSocketsServer.h>
#include <WiFi.h>

#include "config.h"
#include "esp_camera.h"

// WebSocket server for WebRTC signaling
WebSocketsServer webRTC(WEBSOCKET_PORT);

// WebRTC connection state
enum WebRTCState { DISCONNECTED, SIGNALING, CONNECTED };

static WebRTCState webrtcState   = DISCONNECTED;
static uint8_t     currentClient = 0;

// SDP and ICE candidate handling
void handleWebRTCMessage(uint8_t num, uint8_t* payload, size_t length) {
    String message = String(reinterpret_cast<const char*>(payload));

#if ENABLE_METRICS
    VIDEO_LOG("WebRTC message from client %u: %s\n", num, message.c_str());
#endif

    StaticJsonDocument<1024> doc;
    DeserializationError     error = deserializeJson(doc, message);

    if (!error) {
        if (doc.containsKey("type")) {
            String type = doc["type"];

            if (type == "offer") {
                // Handle SDP offer
                String sdp = doc["sdp"];
                // Process SDP offer and generate answer
                // This is a simplified implementation
                webrtcState = CONNECTED;
                currentClient = num;
            }
        }
    }
}

// WebSocket event handler for WebRTC signaling
void webRTCEvent(uint8_t num, WStype_t type, uint8_t* payload, size_t length) {
    switch (type) {
        case WStype_DISCONNECTED: {
            if (num == currentClient) {
                webrtcState   = DISCONNECTED;
                currentClient = 0;
            }
#if ENABLE_METRICS
            VIDEO_LOG("[%u] Disconnected!\n", num);
#endif
            break;
        }

        case WStype_CONNECTED: {
#if ENABLE_METRICS
            VIDEO_LOG("[%u] Connected!\n", num);
#endif
            break;
        }

        case WStype_TEXT: {
            handleWebRTCMessage(num, payload, length);
            break;
        }
    }
}

// Initialize WebRTC video streaming
void initVideoWebRTC() {
    webRTC.begin();
    webRTC.onEvent(webRTCEvent);

#if ENABLE_METRICS
    VIDEO_LOG("WebRTC signaling server started on port %d\n", WEBSOCKET_PORT);
#endif
}

// Send video frame over WebRTC data channel
void sendWebRTCFrame(camera_fb_t* fb) {
    if (webrtcState != CONNECTED || !fb)
        return;

    // In a real implementation, this would:
    // 1. Packetize the frame according to the negotiated codec
    // 2. Create RTP packets
    // 3. Encrypt with SRTP
    // 4. Send over the established ICE connection

    // Here we just send the raw frame over the WebSocket (NOT how WebRTC actually works!)
    if (webRTC.connectedClients() > 0) {
        webRTC.sendBIN(currentClient, fb->buf, fb->len);
    }
}

// Handle WebRTC video streaming
void handleVideoWebRTC() {
    webRTC.loop();

    if (webrtcState != DISCONNECTED) {
#if ENABLE_METRICS
        START_METRIC(frame_capture);
#endif

        camera_fb_t* fb = esp_camera_fb_get();
        if (!fb) {
#if ENABLE_METRICS
            VIDEO_LOG("Camera capture failed\n");
#endif
            return;
        }

#if ENABLE_METRICS
        END_METRIC(frame_capture);
        START_METRIC(frame_send);
#endif

        sendWebRTCFrame(fb);

#if ENABLE_METRICS
        END_METRIC(frame_send);
#endif

        esp_camera_fb_return(fb);
    }

    // Maintain target frame rate
    vTaskDelay(pdMS_TO_TICKS(FRAME_INTERVAL_MS));
}
