#pragma once

#include <WiFi.h>
#include <WiFiUdp.h>

#include "config.h"
#include "esp_camera.h"

// UDP instance for video streaming
WiFiUDP videoUDP;

// Frame counter for sequence numbers
static uint32_t frameCounter = 0;

// Maximum UDP packet size (MTU size - headers)
#define UDP_MAX_PACKET_SIZE 1400

// UDP packet header structure
struct UDPVideoHeader {
    uint32_t frameNumber;   // Frame sequence number
    uint16_t packetNumber;  // Packet sequence number within frame
    uint16_t totalPackets;  // Total packets in this frame
    uint32_t frameSize;     // Total frame size
    uint16_t payloadSize;   // Size of data in this packet
};

// Initialize UDP video streaming
void initVideoUDP()
{
    videoUDP.begin(UDP_VIDEO_PORT);
}

// Send frame data in UDP packets
void sendFrameUDP(camera_fb_t* fb)
{
#if ENABLE_METRICS
    START_METRIC(frame_send);
#endif

    frameCounter++;

    // Calculate number of packets needed
    uint16_t totalPackets = (fb->len + UDP_MAX_PACKET_SIZE - 1) / UDP_MAX_PACKET_SIZE;

    // Send frame data in packets
    for (uint16_t i = 0; i < totalPackets; i++) {
        // Calculate payload size for this packet
        uint16_t payloadSize =
            (i == totalPackets - 1) ? (fb->len - i * UDP_MAX_PACKET_SIZE) : UDP_MAX_PACKET_SIZE;

        // Prepare header
        UDPVideoHeader header = {.frameNumber  = frameCounter,
                                 .packetNumber = i,
                                 .totalPackets = totalPackets,
                                 .frameSize    = fb->len,
                                 .payloadSize  = payloadSize};

        // Send header
        videoUDP.beginPacket(WiFi.broadcastIP(), UDP_VIDEO_PORT);
        videoUDP.write(reinterpret_cast<const uint8_t*>(&header), sizeof(header));

        // Send payload
        videoUDP.write(fb->buf + i * UDP_MAX_PACKET_SIZE, payloadSize);
        videoUDP.endPacket();

        // Small delay to prevent flooding
        delayMicroseconds(100);
    }

#if ENABLE_METRICS
    END_METRIC(frame_send);
    Serial.printf("Frame %u sent in %u packets\n", frameCounter, totalPackets);
#endif
}

// Handle UDP video streaming
void handleVideoUDP()
{
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
#endif

    // Send frame via UDP
    sendFrameUDP(fb);

    esp_camera_fb_return(fb);

    // Maintain target frame rate
    vTaskDelay(pdMS_TO_TICKS(FRAME_INTERVAL_MS));
}
