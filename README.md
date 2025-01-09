# ESP32-CAM Benchmark

Автоматизированный бенчмарк для ESP32-CAM, тестирующий различные протоколы передачи видео и управления.

## Возможности

- **Видео протоколы**:
  - HTTP (MJPEG streaming)
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
- Python 3.9+
- clang-format
- Компилятор C++
- PlatformIO Core

### Оборудование
- ESP32-CAM
- USB-TTL конвертер для прошивки
- Стабильное WiFi подключение

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/your-username/ESP32-CAM_BENCHMARK.git
cd ESP32-CAM_BENCHMARK
```

2. Установите системные зависимости:
```bash
make install-system-deps
```

3. Создайте виртуальное окружение и установите Python зависимости:
```bash
make venv
```

## Конфигурация

1. Настройте WiFi в `bench_config.yml`:
```yaml
wifi:
  ssid: "your_wifi_ssid"
  password: "your_wifi_password"
```

2. При необходимости измените параметры тестов в том же файле:
```yaml
test_combinations:
  - name: "video_only"
    tests:
      - video_protocol: all
        resolutions: [QVGA, VGA]  # Выберите нужные разрешения
```

## Использование

### Разработка

1. Активируйте виртуальное окружение:
```bash
make shell
```

2. Запустите проверки кода:
```bash
make check
```

3. Отформатируйте код:
```bash
make format
```

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
make test
```

2. Результаты будут сохранены в:
- `results/video/` - записи видеопотока
- `results/logs/` - логи работы
- `results/metrics/` - метрики производительности

## Структура проекта

```
ESP32-CAM_BENCHMARK/
├── firmware/
│   └── src/
│       ├── main.cpp              # Основной код
│       ├── camera.h              # Настройки камеры
│       ├── config.h              # Конфигурация
│       ├── video_*.h             # Протоколы видео
│       └── ctrl_*.h              # Протоколы управления
├── tests/                        # Тесты
├── results/                      # Результаты тестов
├── bench_config.yml             # Конфигурация тестов
├── platformio.ini               # Конфигурация PlatformIO
├── requirements.txt             # Python зависимости
└── Makefile                     # Команды сборки
```

## Команды Make

- `make venv` - создание виртуального окружения
- `make build` - сборка прошивки
- `make flash` - прошивка ESP32-CAM
- `make test` - запуск тестов
- `make check` - проверка кода
- `make format` - форматирование кода
- `make clean` - очистка временных файлов
- `make shell` - запуск shell с активированным окружением

## CI/CD

Проект использует GitHub Actions для:
- Проверки стиля кода (C++ и Python)
- Статического анализа
- Сборки прошивки
- Запуска тестов
- Отчетов о покрытии кода

## Метрики

Бенчмарк собирает следующие метрики:
- FPS видеопотока
- Задержки передачи команд
- Загрузка CPU и памяти
- Качество видео
- Стабильность соединения

## Разработка

### Code Style
- C++: Google Style (через clang-format)
- Python: PEP 8 (через black)
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
3. Закоммитьте изменения (`git commit -m 'Add amazing feature'`)
4. Пусните ветку (`git push origin feature/amazing-feature`)
5. Откройте Pull Request 