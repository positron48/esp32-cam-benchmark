#pragma once

#include <ESPAsyncWebServer.h>
#include <WiFi.h>

#include "config.h"
#include "esp_camera.h"

#define BOUNDARY "123456789000000000000987654321"

// Глобальный сервер (extern где-то в вашем main.cpp)
extern AsyncWebServer server;

/*
  Ключевой момент: если заголовок (boundary+Content-Length) больше, чем maxLen,
  мы отправляем его не за один вызов snprintf -> memcpy, а частями.
*/

void initVideoHTTP() {
    Serial.println("Initializing video HTTP...");

    // Маршрут: HTML-страница с <img src="/video">
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
            "</body></html>");
        response->addHeader("Access-Control-Allow-Origin", "*");
        request->send(response);
        Serial.println("Stream page sent");
    });

    // Маршрут /video — отправка MJPEG потока chunked-методом
    server.on("/video", HTTP_GET, [](AsyncWebServerRequest* request) {
        Serial.println("Video stream requested");

        AsyncWebServerResponse* response = request->beginChunkedResponse(
            String("multipart/x-mixed-replace;boundary=") + BOUNDARY,
            [=](uint8_t* buffer, size_t maxLen, size_t index) -> size_t {
                // Статические переменные для хранения контекста между вызовами:
                static camera_fb_t* fb         = nullptr;
                static size_t       offset     = 0;     // сколько уже отправили байт из fb->buf
                static bool         needHeader = true;  // надо ли сформировать новый заголовок?
                static int          failCount  = 0;

                // -- Поля для "частичной" отправки заголовка:
                static char   headerBuf[128];  // буфер, куда сформируем заголовок
                static size_t headerLen  = 0;  // фактическая длина заголовка
                static size_t headerSent = 0;  // сколько байт заголовка уже отправили

                // 1) Если нет текущего кадра, берём новый
                if (!fb) {
                    fb = esp_camera_fb_get();
                    if (!fb) {
                        failCount++;
                        Serial.printf("[video_http] Camera capture failed, failCount=%d\n",
                                      failCount);
                        if (failCount > 5) {
                            vTaskDelay(pdMS_TO_TICKS(100));  // небольшая задержка, если нет кадров
                            failCount = 0;
                        }
                        // Возвращаем 0, чтобы не портить поток
                        return 0;
                    }
                    failCount  = 0;
                    offset     = 0;
                    needHeader = true;
                    headerSent = 0;
                    headerLen  = 0;

                    Serial.printf("[video_http] Got new frame, size=%u\n", fb->len);
                }

                // 2) Сначала, если нужно, готовим и отправляем заголовок
                if (needHeader) {
                    if (headerLen == 0) {
                        // Формируем строку заголовка (boundary + Content-Length + Content-Type)
                        headerLen = snprintf(headerBuf,
                                             sizeof(headerBuf),
                                             "\r\n--%s\r\n"
                                             "Content-Type: image/jpeg\r\n"
                                             "Content-Length: %u\r\n\r\n",
                                             BOUNDARY,
                                             fb->len);
                        // На всякий случай проверяем, не вышли ли за пределы headerBuf
                        if (headerLen >= sizeof(headerBuf)) {
                            Serial.println("[video_http] ERROR: headerBuf too small for header!");
                            // Освобождаем fb и возвращаем 0
                            esp_camera_fb_return(fb);
                            fb = nullptr;
                            return 0;
                        }
                        Serial.printf("[video_http] Header length=%u\n", (unsigned) headerLen);
                    }

                    // Сколько ещё осталось байт заголовка, которые не отправили?
                    size_t remainHeader = headerLen - headerSent;
                    // Отправим кусок, не превышающий maxLen
                    size_t chunkSize = (remainHeader < maxLen) ? remainHeader : maxLen;

                    memcpy(buffer, headerBuf + headerSent, chunkSize);
                    headerSent += chunkSize;

                    // Если закончили отправлять заголовок — переходим к телу JPEG
                    if (headerSent >= headerLen) {
                        needHeader = false;
                    }

                    return chunkSize;
                }

                // 3) Отправляем тело (JPEG) по кускам
                size_t remain = fb->len - offset;  // ещё неотправленные байты кадра
                if (remain == 0) {
                    // Вдруг offset == fb->len, но мы почему-то опять тут
                    // Освободим кадр, чтобы взять следующий
                    esp_camera_fb_return(fb);
                    fb = nullptr;
                    return 0;
                }

                size_t toSend = (remain < maxLen) ? remain : maxLen;
                memcpy(buffer, fb->buf + offset, toSend);
                offset += toSend;

                // Если дошли до конца кадра
                if (offset >= fb->len) {
                    esp_camera_fb_return(fb);
                    fb = nullptr;
                    Serial.println("[video_http] Frame fully sent!");
                }

                return toSend;
            });

        // Доп. заголовки
        response->addHeader("Access-Control-Allow-Origin", "*");
        response->addHeader("Connection", "keep-alive");
        response->addHeader("Cache-Control", "no-cache, no-store, must-revalidate");
        response->addHeader("Pragma", "no-cache");
        response->addHeader("Expires", "0");

        request->send(response);
        Serial.println("Chunked MJPEG stream started");
    });

    Serial.println("Video HTTP initialized");
}

void handleVideoHTTP() {
    // Если хотим ограничить FPS (определено в config.h)
    vTaskDelay(pdMS_TO_TICKS(FRAME_INTERVAL_MS));
}
