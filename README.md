# ESP32-CAM Benchmark

*** в процессе разработки ***

[![CI](https://github.com/positron48/esp32-cam-benchmark/actions/workflows/ci.yml/badge.svg)](https://github.com/positron48/esp32-cam-benchmark/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Автоматизированный бенчмарк для ESP32-CAM, тестирующий различные протоколы передачи видео и управления.

## Возможности

- **Видео протоколы**:
  - HTTP (MJPEG streaming) (реализовано)
  - RTSP (RTP/RTCP)
  - UDP (raw streaming)
  - WebRTC (через WebSocket signaling)

- **Протоколы управления**:
  - HTTP (REST API)
  - UDP (бинарный протокол)
  - WebSocket (JSON messages)

- **Параметры тестирования**:
  - Разрешения: от QQVGA до UXGA
  - Качество JPEG: 10-60
  - Режимы: JPEG/RAW
  - Метрики производительности
  - Комбинированные тесты видео+управление

## Требования

### Системные зависимости
- Python 3.8+
- python3-venv
- Компилятор C++
- PlatformIO Core

### Оборудование
- ESP32-CAM
- USB-TTL конвертер для прошивки
- Стабильное WiFi подключение

## Быстрый старт

1. Клонируйте репозиторий:
```bash
git clone https://github.com/positron48/ESP32-CAM_BENCHMARK.git
cd ESP32-CAM_BENCHMARK
```

2. Установите системные зависимости:
```bash
make install-system-deps
```

3. Установите пакет:
   - Для запуска бенчмарков:
   ```bash
   make install
   ```
   - Для разработки (включая все инструменты):
   ```bash
   make install-dev
   ```

4. Настройте WiFi в `.env`:
```bash
cp .env.example .env
# Отредактируйте .env, указав WIFI_SSID и WIFI_PASSWORD
```

5. Соберите и прошейте:
```bash
make build
make flash
```

## Разработка

### Проверка кода

1. Запустите все проверки:
```bash
make check
```
Это выполнит:
- Статический анализ C++ (cppcheck)
- Проверку стиля C++ (cpplint)
- Линтинг Python (pylint)
- Проверку форматирования Python (black)
- Запуск тестов (pytest)

2. Автоматическое исправление проблем:
```bash
make fix
```
Это исправит:
- Форматирование C++ (clang-format)
- Форматирование Python (black)
- Стиль кода Python (autopep8)

3. Отдельные проверки:
```bash
make lint      # только статический анализ
make format    # только форматирование
make test      # только тесты
```

### Рабочий процесс

1. Активируйте окружение разработки:
```bash
make shell
```

2. Внесите изменения в код

3. Проверьте изменения:
```bash
make check
```

4. Если есть проблемы, исправьте автоматически:
```bash
make fix
```

5. Проверьте и протестируйте исправления

### Сборка и прошивка

1. Соберите прошивку:
```bash
make build
```

2. Прошейте ESP32-CAM:
```bash
make flash
```

### Запуск тестов

1. Запустите полный цикл тестирования:
```bash
esp32cam-benchmark
```

2. Запустите одиночный тест:
```bash
# Минимальный набор параметров
esp32cam-benchmark --single-test --video-protocol HTTP --resolution VGA --quality 30 --duration 30

# С дополнительными параметрами
esp32cam-benchmark --single-test \
  --video-protocol HTTP \
  --resolution VGA \
  --quality 30 \
  --control-protocol UDP \  # опционально
  --duration 60 \          # опционально
  --skip-build            # пропустить сборку прошивки
```

3. Результаты будут сохранены в:
- `results/video/` - записи видеопотока
- `results/logs/` - логи работы
- `results/metrics/` - метрики тестирования в JSON формате

Все файлы именуются по шаблону:
```
{тип}_{дата_время}_{параметры}.{расширение}
```
Где:
- `тип` - video/log/metrics
- `дата_время` - YYYYMMDD_HHMMSS
- `параметры` - комбинация параметров теста:
  - `vid_{протокол}` - протокол видео
  - `ctrl_{протокол}` - протокол управления
  - `res_{разрешение}` - разрешение камеры
  - `q{качество}` - качество JPEG
  - `metrics` - если включен сбор метрик
  - `raw` - если включен RAW режим

Пример:
```
video_20231201_120000_vid_HTTP_res_VGA_q30_metrics.mp4
log_20231201_120000_vid_HTTP_res_VGA_q30_metrics.log
metrics_20231201_120000_vid_HTTP_res_VGA_q30_metrics.json
```

### Параметры командной строки

- Обязательные для одиночного теста:
  - `--video-protocol` - протокол видео (HTTP/RTSP/UDP/WebRTC/none)
  - `--resolution` - разрешение (QQVGA/QVGA/VGA/SVGA/XGA/SXGA/UXGA)
  - `--quality` - качество JPEG (10-60)

- Опциональные:
  - `--control-protocol` - протокол управления (HTTP/UDP/WebSocket/none)
  - `--metrics` - включить сбор метрик
  - `--raw-mode` - включить RAW режим
  - `--duration` - длительность теста в секундах
  - `--skip-build` - пропустить сборку и прошивку (для повторных тестов)

## Структура проекта

```
ESP32-CAM_BENCHMARK/
├── benchmark/                    # Python пакет
│   ├── __init__.py              # Основной модуль
│   ├── benchmark.py             # Класс бенчмарка
│   ├── cli.py                   # CLI интерфейс
│   ├── protocols/               # Протоколы
│   │   ├── video.py            # Видео протоколы
│   │   └── control.py          # Протоколы управления
│   └── utils/                   # Утилиты
│       ├── config.py           # Конфигурация
│       ├── logging.py          # Логирование
│       └── serial.py           # Работа с COM-портом
├── src/                         # Исходники прошивки
│   ├── main.cpp                # Основной код
│   ├── camera.h                # Настройки камеры
│   ├── config.h                # Конфигурация
│   ├── video_*.h               # Протоколы видео
│   └── ctrl_*.h                # Протоколы управления
├── tests/                       # Тесты
├── results/                     # Результаты тестов
├── setup.py                    # Установка пакета
├── platformio.ini              # Конфигурация PlatformIO
└── Makefile                    # Команды сборки
```

## Команды Make

### Основные команды
- `make all` - проверка и сборка
- `make build` - сборка прошивки
- `make flash` - прошивка ESP32-CAM
- `make test` - запуск тестов

### Проверка кода
- `make check` - все проверки
- `make fix` - автоисправление проблем
- `make lint` - статический анализ
- `make format` - форматирование кода

### Разработка
- `make venv` - создание виртуального окружения
- `make shell` - запуск shell с активированным окружением
- `make clean` - очистка временных файлов

## CI/CD

Проект использует GitHub Actions для:
- Проверки стиля кода (C++ и Python)
- Статического анализа
- Сборки прошивки
- Запуска тестов
- Отчетов о покрытии кода

## Метрики

Бенчмарк собирает следующие метрики:

### Метрики видео
- Время подключения к потоку
- Покадровая статистика:
  - Количество кадров за каждую секунду записи
  - Количество пропущенных кадров по секундам
- Статистика FPS:
  - Минимальный/максимальный FPS
  - Стабильность FPS (стандартное отклонение)
  - Средний FPS за весь тест
- Время между кадрами:
  - Минимальное/максимальное время
  - Перцентили (p50, p90, p95, p99)
- Размер видеофайла и битрейт
- Стабильность соединения

### Метрики управления
- Задержки передачи команд
- Процент успешных команд
- Статистика ошибок

### Системные метрики
- Общее время выполнения теста
- Время сборки прошивки
- Время прошивки
- Время загрузки и инициализации
- Загрузка CPU и памяти

Все метрики сохраняются в JSON формате в директории `results/metrics/` и доступны для последующего анализа. Метрики включают детальную статистику по каждой секунде записи, что позволяет строить графики изменения FPS и других параметров во времени.

Пример структуры метрик в JSON:
```json
{
  "video_metrics": {
    "frames_per_second": [
      {"second": 0, "frames": 25, "dropped": 0},
      {"second": 1, "frames": 24, "dropped": 1},
      // ...
    ],
    "fps_stats": {
      "min_fps": 23,
      "max_fps": 25,
      "fps_stability": 0.82
    },
    "frame_time_percentiles_ms": {
      "p50": 40.2,
      "p90": 45.8,
      "p95": 48.3,
      "p99": 52.1
    },
    // другие метрики...
  }
}
```

## Разработка

### Code Style
- C++: Google Style (через clang-format)
  - Сохраняется оригинальный порядок #include директив
  - Используются отступы в 4 пробела
  - Максимальная длина строки 100 символов
- Python: PEP 8 (через black и autopep8)
- Линтеры: cppcheck, cpplint, pylint

### Тестирование
- Unit тесты: pytest
- Покрытие кода: pytest-cov
- CI: GitHub Actions

## Лицензия

MIT License

## Участие в разработке

1. Форкните репозиторий
2. Создайте ветку для фичи (`git checkout -b feature/amazing-feature`)
3. Внесите изменения и проверьте их (`make check` и `make fix`)
4. Закоммитьте изменения (`git commit -m 'Add amazing feature'`)
5. Пусните ветку (`git push origin feature/amazing-feature`)
6. Откройте Pull Request 