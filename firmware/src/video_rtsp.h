#pragma once

#include <WiFi.h>

#include <cstdio>

#include "config.h"
#include "esp_camera.h"

// RTSP server implementation
class RTSPServer {
   private:
    WiFiServer server;
    WiFiClient client;
    bool       clientConnected;
    uint32_t   sessionId;
    uint16_t   sequenceNumber;
    uint32_t   timestamp;

    // RTP packet header (12 bytes)
    struct RTPHeader {
        uint8_t  version_p_x_cc;  // Version (2), Padding (1), Extension (1), CSRC count (4)
        uint8_t  marker_payload;  // Marker (1), Payload type (7)
        uint16_t sequenceNumber;  // Sequence number
        uint32_t timestamp;       // Timestamp
        uint32_t ssrc;            // Synchronization source identifier
    };

    void sendRTSPResponse(const char* response)
    {
        client.print(response);
#if ENABLE_METRICS
        Serial.println(response);
#endif
    }

    void handleOptions()
    {
        char response[256];
        snprintf(response,
                 sizeof(response),
                 "RTSP/1.0 200 OK\r\n"
                 "CSeq: %d\r\n"
                 "Public: OPTIONS, DESCRIBE, SETUP, PLAY, TEARDOWN\r\n"
                 "\r\n",
                 sequenceNumber);
        sendRTSPResponse(response);
    }

    void handleDescribe()
    {
        char sdp[512];
        snprintf(sdp,
                 sizeof(sdp),
                 "v=0\r\n"
                 "o=- %u 1 IN IP4 %s\r\n"
                 "s=ESP32-CAM Stream\r\n"
                 "t=0 0\r\n"
                 "m=video %d RTP/AVP 26\r\n"
                 "c=IN IP4 0.0.0.0\r\n"
                 "a=control:trackID=0\r\n",
                 sessionId,
                 WiFi.localIP().toString().c_str(),
                 RTSP_PORT);

        char response[768];
        snprintf(response,
                 sizeof(response),
                 "RTSP/1.0 200 OK\r\n"
                 "CSeq: %d\r\n"
                 "Content-Type: application/sdp\r\n"
                 "Content-Length: %d\r\n"
                 "\r\n"
                 "%s",
                 sequenceNumber,
                 strlen(sdp),
                 sdp);
        sendRTSPResponse(response);
    }

    void handleSetup()
    {
        char response[256];
        snprintf(response,
                 sizeof(response),
                 "RTSP/1.0 200 OK\r\n"
                 "CSeq: %d\r\n"
                 "Session: %u\r\n"
                 "Transport: RTP/AVP;unicast;client_port=8000-8001\r\n"
                 "\r\n",
                 sequenceNumber,
                 sessionId);
        sendRTSPResponse(response);
    }

    void handlePlay()
    {
        char response[256];
        snprintf(response,
                 sizeof(response),
                 "RTSP/1.0 200 OK\r\n"
                 "CSeq: %d\r\n"
                 "Session: %u\r\n"
                 "Range: npt=0.000-\r\n"
                 "\r\n",
                 sequenceNumber,
                 sessionId);
        sendRTSPResponse(response);
    }

    void handleTeardown()
    {
        char response[256];
        snprintf(response,
                 sizeof(response),
                 "RTSP/1.0 200 OK\r\n"
                 "CSeq: %d\r\n"
                 "Session: %u\r\n"
                 "\r\n",
                 sequenceNumber,
                 sessionId);
        sendRTSPResponse(response);
        client.stop();
        clientConnected = false;
    }

    void sendRTPPacket(const uint8_t* data, size_t len)
    {
        RTPHeader header;
        header.version_p_x_cc = 0x80;  // Version 2, no padding, no extension, no CSRC
        header.marker_payload = 0x1A;  // JPEG payload type
        header.sequenceNumber = htons(sequenceNumber++);
        header.timestamp      = htonl(timestamp);
        header.ssrc           = htonl(0x12345678);  // Fixed SSRC for simplicity

        client.write(reinterpret_cast<const uint8_t*>(&header), sizeof(header));
        client.write(data, len);

        timestamp += 90000 / 30;  // 90kHz clock rate, 30fps
    }

   public:
    RTSPServer()
        : server(RTSP_PORT),
          clientConnected(false),
          sessionId(random(1000000)),
          sequenceNumber(0),
          timestamp(0)
    {
    }

    void begin()
    {
        server.begin();
#if ENABLE_METRICS
        Serial.printf("RTSP server started on port %d\n", RTSP_PORT);
#endif
    }

    void handle()
    {
        if (!clientConnected) {
            client = server.available();
            if (client) {
                clientConnected = true;
#if ENABLE_METRICS
                Serial.println("New RTSP client connected");
#endif
            }
        }

        if (clientConnected && client.available()) {
            String request = client.readStringUntil('\n');
#if ENABLE_METRICS
            Serial.println(request);
#endif

            // Parse request
            if (request.indexOf("OPTIONS") >= 0)
                handleOptions();
            else if (request.indexOf("DESCRIBE") >= 0)
                handleDescribe();
            else if (request.indexOf("SETUP") >= 0)
                handleSetup();
            else if (request.indexOf("PLAY") >= 0)
                handlePlay();
            else if (request.indexOf("TEARDOWN") >= 0)
                handleTeardown();

            // Find CSeq
            while (client.available()) {
                String line = client.readStringUntil('\n');
                if (line.indexOf("CSeq") >= 0) {
                    sequenceNumber = line.substring(line.indexOf(":") + 1).toInt();
                    break;
                }
            }
        }
    }

    void sendFrame(camera_fb_t* fb)
    {
        if (clientConnected) {
            const size_t   maxPacketSize = 1400;  // Keep below typical MTU
            size_t         remaining     = fb->len;
            const uint8_t* ptr           = fb->buf;

            while (remaining > 0) {
                size_t packetSize = remaining > maxPacketSize ? maxPacketSize : remaining;
                sendRTPPacket(ptr, packetSize);
                ptr += packetSize;
                remaining -= packetSize;

                // Small delay between packets
                delayMicroseconds(100);
            }
        }
    }

    bool isClientConnected()
    {
        return clientConnected;
    }
};

// Global RTSP server instance
static RTSPServer rtspServer;

// Initialize RTSP video streaming
void initVideoRTSP()
{
    rtspServer.begin();
}

// Handle RTSP video streaming
void handleVideoRTSP()
{
    rtspServer.handle();

    if (rtspServer.isClientConnected()) {
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

        rtspServer.sendFrame(fb);

#if ENABLE_METRICS
        END_METRIC(frame_send);
#endif

        esp_camera_fb_return(fb);
    }

    // Maintain target frame rate
    vTaskDelay(pdMS_TO_TICKS(FRAME_INTERVAL_MS));
}
