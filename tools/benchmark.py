"""Замер скорости обнаружения на вашем компьютере (для раздела отчёта «быстродействие»).

    python tools/benchmark.py models/ppe.pt models/ppe_openvino_model
    python tools/benchmark.py models/ppe.pt --video data/videos/site.mp4 --frames 100
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from svision.config import PROJECT_ROOT, load_config  # noqa: E402
from svision.detector import YoloDetector  # noqa: E402


def load_frames(video: str | None, count: int) -> list[np.ndarray]:
    if not video:
        print("Видео не указано: замер на случайном кадре 1280x720 (скорость почти не зависит от содержимого).")
        return [np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)] * count
    cap = cv2.VideoCapture(video)
    frames = []
    while len(frames) < count:
        ok, frame = cap.read()
        if not ok:
            break
        frames.append(frame)
    cap.release()
    if not frames:
        sys.exit(f"Не удалось прочитать кадры из {video}")
    return frames


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("models", nargs="+", help="пути к весам: .pt или папка *_openvino_model")
    parser.add_argument("--video")
    parser.add_argument("--frames", type=int, default=60)
    parser.add_argument("--config", default=str(PROJECT_ROOT / "config" / "default.json"))
    args = parser.parse_args()

    cfg = load_config(args.config)
    frames = load_frames(args.video, args.frames)
    print(f"{'модель':<40}{'мс/кадр':>10}{'кадр/с':>9}")
    for model_path in args.models:
        m = cfg.model
        detector = YoloDetector(Path(model_path), m.imgsz, m.conf, m.device, m.class_map, set())
        for frame in frames[:3]:  # прогрев
            detector.detect(frame)
        start = time.perf_counter()
        for frame in frames:
            detector.detect(frame)
        per_frame = (time.perf_counter() - start) / len(frames)
        print(f"{Path(model_path).name:<40}{per_frame * 1000:>10.0f}{1 / per_frame:>9.1f}")


if __name__ == "__main__":
    main()
