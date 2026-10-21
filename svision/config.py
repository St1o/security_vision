"""Загрузка и проверка config/default.json."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .rules import KIND_BY_ROLE, RulesParams, Zone
from .shifts import Shift, parse_hhmm, validate_shifts
from .tracking import TrackerParams

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class ModelConfig:
    path: Path
    imgsz: int
    conf: float
    device: str
    class_map: dict[str, list[str]]
    auto_openvino: bool = True


@dataclass(frozen=True)
class AppConfig:
    root: Path
    object_name: str
    camera_name: str
    source: str | int
    loop: bool
    model: ModelConfig
    zones: tuple[Zone, ...]
    rules: RulesParams
    tracker: TrackerParams
    shifts: tuple[Shift, ...]
    db_path: Path
    snapshots_dir: Path
    exports_dir: Path
    legal_basis: str

    @property
    def required_roles(self) -> set[str]:
        return {role for zone in self.zones for role in zone.required}


def _resolve(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def _parse_source(root: Path, value) -> str | int:
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if text.isdigit():
        return int(text)  # номер веб-камеры
    if "://" in text:
        return text  # rtsp://, http://
    return str(_resolve(root, text))


def _parse_zones(raw_zones) -> tuple[Zone, ...]:
    zones = []
    for item in raw_zones:
        name = item.get("name", "Зона")
        polygon = tuple((float(x), float(y)) for x, y in item.get("polygon", []))
        if len(polygon) < 3:
            raise ConfigError(f"Зона «{name}»: в polygon должно быть минимум 3 точки")
        if any(not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0) for x, y in polygon):
            raise ConfigError(f"Зона «{name}»: координаты polygon задаются в долях кадра от 0 до 1")
        required = tuple(item.get("required", []))
        unknown = [r for r in required if r not in KIND_BY_ROLE]
        if unknown or not required:
            raise ConfigError(
                f"Зона «{name}»: required должен содержать значения из {sorted(KIND_BY_ROLE)}, получено {list(required)}"
            )
        zones.append(Zone(name, polygon, required))
    if not zones:
        raise ConfigError("В конфигурации не задано ни одной зоны (zones)")
    return tuple(zones)


def load_config(path: str | Path, root: Path | None = None) -> AppConfig:
    path = Path(path)
    root = root or PROJECT_ROOT
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigError(f"Файл конфигурации не найден: {path}") from None
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Ошибка в JSON файла {path.name}: {exc}") from None

    model_raw = raw.get("model", {})
    storage_raw = raw.get("storage", {})
    try:
        shifts = tuple(
            Shift(int(s["number"]), s.get("name", f"Смена {s['number']}"), parse_hhmm(s["start"]), parse_hhmm(s["end"]))
            for s in raw.get("shifts", [])
        )
        validate_shifts(shifts)
        return AppConfig(
            root=root,
            object_name=raw.get("object_name", "Строительная площадка"),
            camera_name=raw.get("camera_name", "Камера 1"),
            source=_parse_source(root, raw.get("source", 0)),
            loop=bool(raw.get("loop", False)),
            model=ModelConfig(
                path=_resolve(root, model_raw.get("path", "models/ppe.pt")),
                imgsz=int(model_raw.get("imgsz", 640)),
                conf=float(model_raw.get("conf", 0.35)),
                device=str(model_raw.get("device", "cpu")),
                class_map={k: list(v) for k, v in model_raw.get("class_map", {}).items()},
                auto_openvino=bool(model_raw.get("auto_openvino", True)),
            ),
            zones=_parse_zones(raw.get("zones", [])),
            rules=RulesParams(**raw.get("rules", {})),
            tracker=TrackerParams(**raw.get("tracker", {})),
            shifts=shifts,
            db_path=_resolve(root, storage_raw.get("db", "data/violations.db")),
            snapshots_dir=_resolve(root, storage_raw.get("snapshots", "data/snapshots")),
            exports_dir=_resolve(root, storage_raw.get("exports", "exports")),
            legal_basis=raw.get("report", {}).get("legal_basis", ""),
        )
    except ConfigError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise ConfigError(f"Некорректная конфигурация ({path.name}): {exc}") from None
