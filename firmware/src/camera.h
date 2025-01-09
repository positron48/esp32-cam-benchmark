#pragma once

#include <Arduino.h>

// Camera control state
static struct {
    int pan;         // -100 to 100
    int tilt;        // -100 to 100
    int zoom;        // -100 to 100
    int led;         // 0 or 1
    int brightness;  // 0 to 100
} camera_state = {0, 0, 0, 0, 50};

void camera_pan(int value)
{
    camera_state.pan = constrain(value, -100, 100);
}

void camera_tilt(int value)
{
    camera_state.tilt = constrain(value, -100, 100);
}

void camera_zoom(int value)
{
    camera_state.zoom = constrain(value, -100, 100);
}

void camera_led(int value)
{
    camera_state.led = value ? 1 : 0;
#ifdef LED_BUILTIN
    digitalWrite(LED_BUILTIN, camera_state.led);
#endif
}

void camera_brightness(int value)
{
    camera_state.brightness = constrain(value, 0, 100);
}

int camera_get_pan()
{
    return camera_state.pan;
}

int camera_get_tilt()
{
    return camera_state.tilt;
}

int camera_get_zoom()
{
    return camera_state.zoom;
}

int camera_get_led()
{
    return camera_state.led;
}

int camera_get_brightness()
{
    return camera_state.brightness;
}

void camera_init()
{
#ifdef LED_BUILTIN
    pinMode(LED_BUILTIN, OUTPUT);
    digitalWrite(LED_BUILTIN, LOW);
#endif
}
