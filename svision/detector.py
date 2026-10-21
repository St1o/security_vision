"""Обёртка над YOLO (ultralytics): кадр -> список Detection с ролями person/helmet/vest/..."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

from .rules import Detection


class ModelError(RuntimeError):
    pass


def _norm(name: str) -> str:
    return re.sub(r"[\s_\-]+", " ", name.strip().lower())


def build_class_roles(names: Mapping[int, str], class_map: Mapping[str, Sequence[str]]) -> dict[int, str]:
    """Сопоставляет классы модели ролям программы по названиям (регистр и дефисы не важны)."""
    lookup: dict[str, str] = {}
    for role, aliases in class_map.items():
        for alias in aliases:
            lookup[_norm(alias)] = role
    return {cid: lookup[_norm(n)] for cid, n in names.items() if _norm(n) in lookup}


def check_roles(roles: Mapping[int, str], required: set[str], model_names: Mapping[int, str]) -> None:
    found = set(roles.values())
    missing = []
    if "person" not in found:
        missing.append("person (человек)")
    for role in sorted(required):
        if role not in found and ("no_" + role) not in found:
            missing.append(role)
    if missing:
        raise ModelError(
            "В модели нет нужных классов: " + ", ".join(missing) + ". "
            f"Классы модели: {sorted(model_names.values())}. "
            "Исправьте model.class_map в config/default.json."
        )


def prefer_openvino(path: Path) -> Path:
    """Если рядом с весами .pt лежит экспортированная папка <имя>_openvino_model, берёт её: на CPU Intel она быстрее."""
    path = Path(path)
    exported = path.with_name(path.stem + "_openvino_model")
    if path.suffix == ".pt" and exported.is_dir() and any(exported.glob("*.xml")):
        return exported
    return path


class YoloDetector:
    def __init__(self, path: Path, imgsz: int, conf: float, device: str,
                 class_map: Mapping[str, Sequence[str]], required_roles: set[str]):
        if not Path(path).exists():
            raise ModelError(
                f"Файл модели не найден: {path}. Обучите модель (training/train_ppe_colab.ipynb) "
                "и положите best.pt в папку models/ под именем ppe.pt."
            )
        from ultralytics import YOLO  # тяжёлый импорт, поэтому здесь

        self.model = YOLO(str(path))
        self.imgsz, self.conf, self.device = imgsz, conf, device
        names = self.model.names  # у экспортированных моделей каждое обращение к names может заново загружать модель
        self.roles = build_class_roles(names, class_map)
        check_roles(self.roles, required_roles, names)

    def detect(self, frame: np.ndarray) -> list[Detection]:
        result = self.model.predict(frame, imgsz=self.imgsz, conf=self.conf,
                                    device=self.device, verbose=False)[0]
        if result.boxes is None or len(result.boxes) == 0:
            return []
        xyxy = result.boxes.xyxy.cpu().numpy()
        confs = result.boxes.conf.cpu().numpy()
        classes = result.boxes.cls.cpu().numpy().astype(int)
        detections = []
        for box, conf, cid in zip(xyxy, confs, classes):
            role = self.roles.get(int(cid))
            if role is not None:
                detections.append(Detection(role, float(conf), tuple(float(v) for v in box)))
        return detections
