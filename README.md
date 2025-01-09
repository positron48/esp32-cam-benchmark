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
git clone https://github.com/your-username/ESP32-CAM_BENCHMARK.git
cd ESP32-CAM_BENCHMARK
```

2. Установите системные зависимости:
```bash
make install-system-deps
```

3. Создайте виртуальное окружение и установите зависимости:
```bash
make venv
```

4. Настройте WiFi в `bench_config.yml`:
```yaml
wifi:
  ssid: "your_wifi_ssid"
  password: "your_wifi_password"
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
- FPS видеопотока
- Задержки передачи команд
- Загрузка CPU и памяти
- Качество видео
- Стабильность соединения

## Разработка

### Code Style
- C++: Google Style (через clang-format)
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