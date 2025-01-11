"""Video protocol functionality for ESP32-CAM benchmark with real-time stretch."""

import json
import os
import statistics
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import cv2


def test_video(
    ip_address: str,
    protocol: str,
    resolution: str,
    quality: int,
    raw_mode: bool,
    duration: int,
    logger: Any
) -> Dict[str, Any]:
    """Test video streaming with real-time stretch (duplicates frames to preserve real duration).

    Args:
        ip_address: Device IP address
        protocol: Video protocol to test
        resolution: Camera resolution
        quality: JPEG quality
        raw_mode: Whether to use raw mode
        duration: Test duration in seconds
        logger: Logger instance

    Returns:
        Dictionary with test results
    """
    # Мы добавляем 2 секунды для неполных первой и последней секунд
    actual_duration = duration + 2

    logger.info(
        "Starting video test (with real-time stretch): protocol=%s, resolution=%s, quality=%d, raw=%s",
        protocol,
        resolution,
        quality,
        raw_mode,
    )

    # Инициализируем метрики
    metrics = {
        "connection_time": 0,
        "total_frames": 0,
        "avg_fps": 0,
        "dropped_frames": 0,
        "total_size_mb": 0,
        "bitrate_mbps": 0,
        "test_duration": 0,
        "frames_per_second": [],  # frames captured in each second
    }

    # Формируем URL
    if protocol == "HTTP":
        url = f"http://{ip_address}/video"
    elif protocol == "RTSP":
        url = f"rtsp://{ip_address}:8554/video"
    elif protocol == "UDP":
        url = f"udp://{ip_address}:5000"
    elif protocol == "WebRTC":
        url = f"ws://{ip_address}:8080/video"
    else:
        raise ValueError(f"Unsupported video protocol: {protocol}")

    # Создаём директорию для результатов
    output_dir = Path("results/video")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / (
        f'video_{datetime.now().strftime("%Y%m%d_%H%M%S")}_{protocol}_{resolution}_q{quality}.mp4'
    )

    # Открываем поток
    connection_start = time.time()
    logger.info("Opening video stream: %s", url)
    cap = cv2.VideoCapture(url)
    if not cap.isOpened():
        raise RuntimeError("Failed to open video stream")
    metrics["connection_time"] = time.time() - connection_start

    # Свойства видеопотока
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    nominal_fps = 30  # Целевой FPS, в котором мы будем сохранять видео
    logger.info("Video properties: %dx%d, writing at nominal %d fps", frame_width, frame_height, nominal_fps)

    # Настраиваем VideoWriter
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(output_path), fourcc, nominal_fps, (frame_width, frame_height))

    # Доп. переменные для метрик
    frames_captured = 0
    failed_reads = 0
    start_time = time.time()
    last_frame_time = start_time
    frame_times = []
    frames_by_second = {}
    first_frame = True
    last_log_second = -1
    last_log_frames = 0

    # Основной цикл чтения
    while (time.time() - start_time) < actual_duration:
        ret, frame = cap.read()
        current_time = time.time()
        elapsed = current_time - start_time

        # Пропускаем неполную первую секунду
        if first_frame:
            first_frame = False
            last_frame_time = current_time
            continue

        if not ret:
            logger.error("Failed to read frame at %.2f seconds", elapsed)
            failed_reads += 1
            continue

        # Вычисляем dt
        dt = current_time - last_frame_time
        last_frame_time = current_time

        # Считаем кадры, пришедшие от ESP
        frames_captured += 1
        frame_times.append(dt)

        second = int(elapsed)
        if second not in frames_by_second:
            frames_by_second[second] = {"frames": 0, "dropped": 0}
        frames_by_second[second]["frames"] += 1

        # ----------- Логика дублирования -----------
        ideal_dt = 1.0 / nominal_fps
        duplicates = int(round(dt / ideal_dt))
        if duplicates < 1:
            duplicates = 1

        for _ in range(duplicates):
            out.write(frame)
        # -------------------------------------------

        # Логгирование каждые секунду (примерно)
        if second > last_log_second and second > 0:
            frames_this_second = frames_captured - last_log_frames
            avg_fps = frames_captured / elapsed
            logger.info(
                "Second %d: captured %d raw frames (avg raw: %.2f fps), dt=%.3fs => duplicates=%d",
                second,
                frames_this_second,
                avg_fps,
                dt,
                duplicates
            )
            last_log_second = second
            last_log_frames = frames_captured

    # Завершение
    cap.release()
    out.release()

    test_duration = time.time() - start_time
    file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0

    # Подсчёт статистики по временам между кадрами
    if frame_times:
        frame_times_ms = [t * 1000 for t in frame_times]
        frame_times_ms.sort()
        frame_time_percentiles = {
            "p50": frame_times_ms[len(frame_times_ms) // 2],
            "p90": frame_times_ms[int(len(frame_times_ms) * 0.9)],
            "p95": frame_times_ms[int(len(frame_times_ms) * 0.95)],
            "p99": frame_times_ms[int(len(frame_times_ms) * 0.99)],
        }
    else:
        frame_time_percentiles = {"p50": 0, "p90": 0, "p95": 0, "p99": 0}

    # Собираем FPS-сводку
    complete_seconds_fps = []
    for second in sorted(frames_by_second.keys()):
        if second > 0 and second <= duration:
            complete_seconds_fps.append(frames_by_second[second]["frames"])
            metrics["frames_per_second"].append({
                "second": second,
                "frames": frames_by_second[second]["frames"],
                "dropped": frames_by_second[second]["dropped"],
            })

    if complete_seconds_fps:
        complete_seconds_fps.sort(reverse=True)
        fps_percentiles = {
            "p50": complete_seconds_fps[len(complete_seconds_fps) // 2],
            "p75": complete_seconds_fps[int(len(complete_seconds_fps) * 0.75)],
            "p90": complete_seconds_fps[int(len(complete_seconds_fps) * 0.9)],
            "p95": complete_seconds_fps[int(len(complete_seconds_fps) * 0.95)],
            "p99": complete_seconds_fps[int(len(complete_seconds_fps) * 0.99)],
        }
    else:
        fps_percentiles = {"p50": 0, "p75": 0, "p90": 0, "p95": 0, "p99": 0}

    fps_stats = {
        "min_fps": min(complete_seconds_fps) if complete_seconds_fps else 0,
        "max_fps": max(complete_seconds_fps) if complete_seconds_fps else 0,
        "fps_stability": round(statistics.stdev(complete_seconds_fps), 2) if len(complete_seconds_fps) > 1 else 0,
        "percentiles": fps_percentiles,
    }

    metrics.update({
        "total_frames": frames_captured,             # сырые кадры от ESP
        "dropped_frames": failed_reads,              # не прочитанные (ret=False)
        "avg_fps": (
            sum(complete_seconds_fps) / len(complete_seconds_fps)
            if len(complete_seconds_fps) > 0 else 0
        ),
        "frame_time_min_ms": min(frame_times) * 1000 if frame_times else 0,
        "frame_time_max_ms": max(frame_times) * 1000 if frame_times else 0,
        "frame_time_percentiles_ms": frame_time_percentiles,
        "total_size_mb": file_size / (1024 * 1024),
        "bitrate_mbps": (file_size * 8) / (test_duration * 1024 * 1024) if test_duration > 0 else 0,
        "test_duration": test_duration,
        "analyzed_duration": duration,
        "fps_stats": fps_stats,
        "video_file": str(output_path),
    })

    _log_video_metrics(metrics, logger)
    return metrics


def _log_video_metrics(metrics: Dict[str, Any], logger: Any) -> None:
    """Log video capture metrics."""
    logger.info("Video capture completed. Metrics:")
    logger.info("  Connection time: %.2f seconds", metrics["connection_time"])
    logger.info("  Total raw frames: %d", metrics["total_frames"])
    logger.info(
        "  Dropped frames: %d (%.1f%%)",
        metrics["dropped_frames"],
        (
            (metrics["dropped_frames"] / (metrics["total_frames"] + metrics["dropped_frames"]) * 100)
            if metrics["total_frames"] > 0
            else 0
        ),
    )
    logger.info("  Average raw FPS (ESP side): %.2f", metrics["avg_fps"])
    logger.info(
        "  FPS range (raw): %.1f-%.1f (stability: ±%.1f)",
        metrics["fps_stats"]["min_fps"],
        metrics["fps_stats"]["max_fps"],
        metrics["fps_stats"]["fps_stability"],
    )
    logger.info("  FPS percentiles (raw frames / second):")
    logger.info("    50%% of time: ≥%.1f fps", metrics["fps_stats"]["percentiles"]["p50"])
    logger.info("    75%% of time: ≥%.1f fps", metrics["fps_stats"]["percentiles"]["p75"])
    logger.info("    90%% of time: ≥%.1f fps", metrics["fps_stats"]["percentiles"]["p90"])
    logger.info("    95%% of time: ≥%.1f fps", metrics["fps_stats"]["percentiles"]["p95"])
    logger.info("    99%% of time: ≥%.1f fps", metrics["fps_stats"]["percentiles"]["p99"])

    logger.info(
        "  Frame times - min: %.1fms, max: %.1fms",
        metrics["frame_time_min_ms"],
        metrics["frame_time_max_ms"],
    )
    logger.info(
        "  Frame time percentiles - p50: %.1fms, p90: %.1fms, p95: %.1fms, p99: %.1fms",
        metrics["frame_time_percentiles_ms"]["p50"],
        metrics["frame_time_percentiles_ms"]["p90"],
        metrics["frame_time_percentiles_ms"]["p95"],
        metrics["frame_time_percentiles_ms"]["p99"],
    )
    logger.info("  Video size: %.2f MB", metrics["total_size_mb"])
    logger.info("  Bitrate: %.2f Mbps", metrics["bitrate_mbps"])
    logger.info(
        "  Total test duration: %.2f seconds (analyzed %d seconds)",
        metrics["test_duration"],
        metrics["analyzed_duration"],
    )
    logger.info("  Video saved to: %s", metrics["video_file"])
