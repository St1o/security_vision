"""Конвертирует веса .pt в формат OpenVINO. На части процессоров он быстрее, на других нестабилен: сравните tools/benchmark.py (медиану и среднее).

    python tools/export_openvino.py                 # models/ppe.pt -> models/ppe_openvino_model/
    python tools/export_openvino.py models/ppe.pt

Чтобы программа использовала папку models/ppe_openvino_model, поставьте model.auto_openvino = true в config/default.json.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from svision.config import PROJECT_ROOT, load_config  # noqa: E402


def main() -> None:
    cfg = load_config(PROJECT_ROOT / "config" / "default.json")
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT_ROOT / "models" / "ppe.pt"
    if not source.exists():
        sys.exit(f"Файл не найден: {source}")
    from ultralytics import YOLO

    result = YOLO(str(source)).export(format="openvino", imgsz=cfg.model.imgsz)
    print("Готово:", result)
    print("Чтобы программа использовала эту папку, поставьте model.auto_openvino = true в config/default.json.")


if __name__ == "__main__":
    main()
