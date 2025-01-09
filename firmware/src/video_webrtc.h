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
void handleWebRTCMessage(uint8_t num, uint8_t* payload, size_t length)
{
    String message = String(reinterpret_cast<const char*>(payload));

#if ENABLE_METRICS
    Serial.printf("WebRTC message from client %u: %s\n", num, message.c_str());
#endif

    StaticJsonDocument<1024> doc;
    DeserializationError     error = deserializeJson(doc, message);

    if (!error) {
        if (doc.containsKey("type")) {
            String type = doc["type"];

            if (type == "offer") {
                // Handle SDP offer
                String sdp = doc["sdp"];

                // Create answer (simplified - in real implementation, this would involve
                // proper WebRTC stack with codec negotiation, etc.)
                StaticJsonDocument<1024> answer;
                answer["type"] = "answer";
                answer["sdp"] =
                    "v=0\r\n"
                    "o=- " +
                    String(random(1000000)) +
                    " 2 IN IP4 127.0.0.1\r\n"
                    "s=-\r\n"
                    "t=0 0\r\n"
                    "a=group:BUNDLE video\r\n"
                    "m=video 9 UDP/TLS/RTP/SAVPF 96\r\n"
                    "c=IN IP4 0.0.0.0\r\n"
                    "a=rtcp:9 IN IP4 0.0.0.0\r\n"
                    "a=ice-ufrag:" +
                    String(random(0xFFFFFFFF), HEX) +
                    "\r\n"
                    "a=ice-pwd:" +
                    String(random(0xFFFFFFFF), HEX) +
                    "\r\n"
                    "a=fingerprint:sha-256 " +
                    String(random(0xFFFFFFFF), HEX) +
                    "\r\n"
                    "a=setup:active\r\n"
                    "a=mid:video\r\n"
                    "a=sendonly\r\n"
                    "a=rtcp-mux\r\n"
                    "a=rtcp-rsize\r\n";

                String response;
                serializeJson(answer, response);
                webRTC.sendTXT(num, response);

                webrtcState   = SIGNALING;
                currentClient = num;
            }
            else if (type == "ice-candidate") {
                // Handle ICE candidate
                if (doc.containsKey("candidate")) {
                    String candidate = doc["candidate"];

                    // In a real implementation, we would add this candidate to the
                    // WebRTC connection. Here we just acknowledge it.
                    StaticJsonDocument<200> ack;
                    ack["type"] = "ice-ack";

                    String response;
                    serializeJson(ack, response);
                    webRTC.sendTXT(num, response);
                }
            }
        }
    }
}

// WebSocket event handler for WebRTC signaling
void webRTCEvent(uint8_t num, WStype_t type, uint8_t* payload, size_t length)
{
    switch (type) {
        case WStype_DISCONNECTED: {
            if (num == currentClient) {
                webrtcState   = DISCONNECTED;
                currentClient = 0;
            }
#if ENABLE_METRICS
            Serial.printf("[%u] Disconnected!\n", num);
#endif
            break;
        }

        case WStype_CONNECTED: {
#if ENABLE_METRICS
            Serial.printf("[%u] Connected!\n", num);
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
void initVideoWebRTC()
{
    webRTC.begin();
    webRTC.onEvent(webRTCEvent);

#if ENABLE_METRICS
    Serial.printf("WebRTC signaling server started on port %d\n", WEBSOCKET_PORT);
#endif
}

// Send video frame over WebRTC data channel
// Note: This is a simplified implementation. A real WebRTC implementation would:
// 1. Use proper RTP/SRTP for media transport
// 2. Handle ICE for NAT traversal
// 3. Implement proper DTLS-SRTP for security
// 4. Handle codec negotiation and packetization
void sendWebRTCFrame(camera_fb_t* fb)
{
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
void handleVideoWebRTC()
{
    webRTC.loop();

    if (webrtcState != DISCONNECTED) {
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

        sendWebRTCFrame(fb);

#if ENABLE_METRICS
        END_METRIC(frame_send);
#endif

        esp_camera_fb_return(fb);
    }

    // Maintain target frame rate
    vTaskDelay(pdMS_TO_TICKS(FRAME_INTERVAL_MS));
}
