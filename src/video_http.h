#pragma once

#include <ESPAsyncWebServer.h>
#include <WiFi.h>
#include "config.h"
#include "esp_camera.h"

// Настраиваем разделитель для multipart:
#define BOUNDARY "123456789000000000000987654321"

// Глобальный сервер (объявлен где-то как extern):
extern AsyncWebServer server;

// Инициализация видеострима по HTTP
void initVideoHTTP() {
    Serial.println("Initializing video HTTP...");

    // Простой маршрут, который отдаёт HTML-страничку с <img src="/video">
    server.on("/stream", HTTP_GET, [](AsyncWebServerRequest* request) {
        Serial.println("Stream page requested");
        AsyncWebServerResponse* response = request->beginResponse(
            200,
            "text/html",
            "<html><head>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            "<style>img { width: 100%; height: auto; }</style>"
            "</head><body>"
            "<h1>ESP32-CAM MJPEG Stream</h1>"
            "<img src='/video' />"
            "</body></html>"
        );
        response->addHeader("Access-Control-Allow-Origin", "*");
        request->send(response);
        Serial.println("Stream page sent");
    });

    // Маршрут /video, который будет непрерывно отдавать кадры (Chunked Response)
    server.on("/video", HTTP_GET, [](AsyncWebServerRequest *request) {
        Serial.println("Video stream requested");

        // Создаём потоковый (chunked) ответ с типом "multipart/x-mixed-replace"
        AsyncWebServerResponse* response = request->beginChunkedResponse(
            String("multipart/x-mixed-replace;boundary=") + BOUNDARY,
            [=](uint8_t *buffer, size_t maxLen, size_t index) -> size_t {
                // Статические переменные, чтобы хранить состояние между вызовами
                static camera_fb_t* fb     = nullptr;  // текущий кадр
                static size_t offset       = 0;         // сколько байт уже отправили
                static bool sendingHeader  = true;      // отправляем ли сейчас заголовки

                // Если кадр отсутствует, значит, надо взять новый
                if (!fb) {
                    fb = esp_camera_fb_get();
                    if (!fb) {
                        Serial.println("Camera capture failed");
                        return 0; // отправим 0, сервер подождёт следующего колбэка
                    }
                    offset = 0;
                    sendingHeader = true;
                }

                // Если надо отправить заголовок (boundary + Content-Type + Content-Length)
                if (sendingHeader) {
                    // Формируем boundary и заголовки (Content-Type, Content-Length)
                    int len = snprintf(
                        (char*)buffer,
                        maxLen,
                        "\r\n--%s\r\n"
                        "Content-Type: image/jpeg\r\n"
                        "Content-Length: %u\r\n\r\n",
                        BOUNDARY,
                        fb->len
                    );
                    sendingHeader = false;
                    return len; 
                }

                // Отправляем часть JPEG-данных кадра
                size_t remain = fb->len - offset;  // сколько байт осталось отправить
                size_t toSend = (remain < maxLen) ? remain : maxLen;

                memcpy(buffer, fb->buf + offset, toSend);
                offset += toSend;

                // Если весь кадр отправлен — освобождаем буфер и обнуляем указатель
                if (offset >= fb->len) {
                    esp_camera_fb_return(fb);
                    fb = nullptr;
                }

                return toSend; // возвращаем, сколько реально записали
            }
        );

        // Добавляем необходимые заголовки
        response->addHeader("Access-Control-Allow-Origin", "*");
        response->addHeader("Connection", "keep-alive");
        response->addHeader("Cache-Control", "no-cache, no-store, must-revalidate");
        response->addHeader("Pragma", "no-cache");
        response->addHeader("Expires", "0");

        // Отправляем потоковое видео
        request->send(response);
        Serial.println("Chunked MJPEG stream started");
    });

    Serial.println("Video HTTP initialized");
}

// При желании можно управлять задержкой между кадрами (FPS).
void handleVideoHTTP() {
    // FRAME_INTERVAL_MS определяется в config.h
    vTaskDelay(pdMS_TO_TICKS(FRAME_INTERVAL_MS));
}
