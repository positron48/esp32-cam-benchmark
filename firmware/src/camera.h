#pragma once

#include "esp_camera.h"
#include "config.h"

// ESP32-CAM camera pins
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// Camera configuration structure
static camera_config_t camera_config = {
    .pin_pwdn = PWDN_GPIO_NUM,
    .pin_reset = RESET_GPIO_NUM,
    .pin_xclk = XCLK_GPIO_NUM,
    .pin_sscb_sda = SIOD_GPIO_NUM,
    .pin_sscb_scl = SIOC_GPIO_NUM,
    .pin_d7 = Y9_GPIO_NUM,
    .pin_d6 = Y8_GPIO_NUM,
    .pin_d5 = Y7_GPIO_NUM,
    .pin_d4 = Y6_GPIO_NUM,
    .pin_d3 = Y5_GPIO_NUM,
    .pin_d2 = Y4_GPIO_NUM,
    .pin_d1 = Y3_GPIO_NUM,
    .pin_d0 = Y2_GPIO_NUM,
    .pin_vsync = VSYNC_GPIO_NUM,
    .pin_href = HREF_GPIO_NUM,
    .pin_pclk = PCLK_GPIO_NUM,
    .xclk_freq_hz = 20000000,
    .ledc_timer = LEDC_TIMER_0,
    .ledc_channel = LEDC_CHANNEL_0,
    .pixel_format = RAW_MODE ? PIXFORMAT_RGB565 : PIXFORMAT_JPEG,
    .frame_size = FRAMESIZE_VGA,  // Will be set based on CAMERA_RESOLUTION
    .jpeg_quality = JPEG_QUALITY,
    .fb_count = 2,
    .grab_mode = CAMERA_GRAB_WHEN_EMPTY
};

// Initialize camera with current settings
bool initCamera() {
    // Set resolution based on configuration
    #if CAMERA_RESOLUTION == QQVGA
    camera_config.frame_size = FRAMESIZE_QQVGA;
    #elif CAMERA_RESOLUTION == QVGA
    camera_config.frame_size = FRAMESIZE_QVGA;
    #elif CAMERA_RESOLUTION == VGA
    camera_config.frame_size = FRAMESIZE_VGA;
    #elif CAMERA_RESOLUTION == SVGA
    camera_config.frame_size = FRAMESIZE_SVGA;
    #elif CAMERA_RESOLUTION == XGA
    camera_config.frame_size = FRAMESIZE_XGA;
    #elif CAMERA_RESOLUTION == SXGA
    camera_config.frame_size = FRAMESIZE_SXGA;
    #elif CAMERA_RESOLUTION == UXGA
    camera_config.frame_size = FRAMESIZE_UXGA;
    #endif

    // Initialize camera
    esp_err_t err = esp_camera_init(&camera_config);
    if (err != ESP_OK) {
        #if ENABLE_METRICS
        Serial.printf("Camera init failed with error 0x%x", err);
        #endif
        return false;
    }

    // Get camera sensor
    sensor_t * s = esp_camera_sensor_get();
    if (s) {
        // Apply additional settings
        s->set_brightness(s, 0);     // -2 to 2
        s->set_contrast(s, 0);       // -2 to 2
        s->set_saturation(s, 0);     // -2 to 2
        s->set_special_effect(s, 0); // 0 to 6 (0 - No Effect, 1 - Negative, 2 - Grayscale, 3 - Red Tint, 4 - Green Tint, 5 - Blue Tint, 6 - Sepia)
        s->set_whitebal(s, 1);       // 0 = disable , 1 = enable
        s->set_awb_gain(s, 1);       // 0 = disable , 1 = enable
        s->set_wb_mode(s, 0);        // 0 to 4 - if awb_gain enabled (0 - Auto, 1 - Sunny, 2 - Cloudy, 3 - Office, 4 - Home)
        s->set_exposure_ctrl(s, 1);  // 0 = disable , 1 = enable
        s->set_aec2(s, 0);          // 0 = disable , 1 = enable
        s->set_gain_ctrl(s, 1);      // 0 = disable , 1 = enable
        s->set_agc_gain(s, 0);       // 0 to 30
        s->set_gainceiling(s, (gainceiling_t)0);  // 0 to 6
        s->set_bpc(s, 0);           // 0 = disable , 1 = enable
        s->set_wpc(s, 1);           // 0 = disable , 1 = enable
        s->set_raw_gma(s, 1);       // 0 = disable , 1 = enable
        s->set_lenc(s, 1);          // 0 = disable , 1 = enable
        s->set_hmirror(s, 0);       // 0 = disable , 1 = enable
        s->set_vflip(s, 0);         // 0 = disable , 1 = enable
        s->set_dcw(s, 1);           // 0 = disable , 1 = enable
        s->set_colorbar(s, 0);      // 0 = disable , 1 = enable
    }

    return true;
} 