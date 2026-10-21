"""Фоновый поток: чтение видео -> обнаружение -> правила -> запись нарушений в журнал."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

import cv2
import numpy as np
from PySide6.QtCore import QBuffer, QIODevice, QThread, Signal

from ..config import AppConfig
from ..pipeline import Detector, FrameAnalysis, Pipeline
from ..rules import KIND_LABELS, ViolationEngine, ViolationEvent
from ..shifts import shift_for
from ..storage import Storage
from ..tracking import IoUTracker
from .overlay import render_frame

MAX_UI_FPS = 20.0


@dataclass
class FrameInfo:
    fps: float = 0.0
    persons: int = 0
    violators: int = 0
    rows: list[tuple[str, str, str, str, str]] = field(default_factory=list)


class VideoWorker(QThread):
    frame_ready = Signal(object, object)   # QImage, FrameInfo
    violation_logged = Signal(object)      # ViolationRecord
    status = Signal(str)
    failed = Signal(str)

    def __init__(self, cfg: AppConfig, storage: Storage, source: str | int,
                 detector_factory: Callable[[], Detector], parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.storage = storage
        self.source = source
        self._detector_factory = detector_factory
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        cap = None
        try:
            self.status.emit("Загрузка модели…")
            detector = self._detector_factory()
            pipeline = Pipeline(detector, IoUTracker(self.cfg.tracker),
                                ViolationEngine(self.cfg.zones, self.cfg.rules))
            cap = cv2.VideoCapture(self.source)
            if not cap.isOpened():
                raise RuntimeError(f"Не удалось открыть источник видео: {self.source}")
            is_file = isinstance(self.source, str) and "://" not in self.source
            if not is_file:
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            src_fps = cap.get(cv2.CAP_PROP_FPS)
            src_fps = src_fps if src_fps and 1.0 < src_fps < 240.0 else 25.0
            self.status.emit("Идёт контроль")
            self._loop(cap, pipeline, is_file, src_fps)
        except Exception as exc:  # noqa: BLE001 - любую ошибку показываем пользователю
            self.failed.emit(str(exc))
        finally:
            if cap is not None:
                cap.release()

    def _loop(self, cap, pipeline: Pipeline, is_file: bool, src_fps: float) -> None:
        t0 = time.monotonic()
        wall0 = datetime.now()
        frame_idx = 0
        db_ids: dict[int, int] = {}
        fps = 0.0
        last_tick = time.monotonic()
        last_emit = 0.0
        last_analysis: FrameAnalysis | None = None
        last_t = 0.0

        while not self._stop:
            now = time.monotonic() - t0
            if is_file:
                due = int(now * src_fps)
                while frame_idx < due and cap.grab():  # не успеваем -> пропускаем кадры, чтобы идти в реальном времени
                    frame_idx += 1
                wait = frame_idx / src_fps - now
                if wait > 0:
                    time.sleep(wait)
                    now = time.monotonic() - t0
            ok, frame = cap.read()
            if is_file:
                frame_idx += 1
            if not ok:
                if is_file and self.cfg.loop:
                    self._finish_open(db_ids, last_analysis, last_t)
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    frame_idx, t0, wall0 = 0, time.monotonic(), datetime.now()
                    pipeline.reset()
                    last_analysis = None
                    continue
                self.status.emit("Видео закончилось" if is_file else "Нет сигнала с камеры")
                break

            analysis = pipeline.process(frame, now)
            last_analysis, last_t = analysis, now
            self._log_events(analysis, frame, wall0, db_ids)

            tick = time.monotonic()
            dt = tick - last_tick
            last_tick = tick
            if dt > 0:
                fps = 1.0 / dt if fps == 0.0 else 0.9 * fps + 0.1 / dt

            if tick - last_emit >= 1.0 / MAX_UI_FPS:
                last_emit = tick
                self.frame_ready.emit(render_frame(frame, analysis, self.cfg.zones),
                                      self._info(analysis, now, wall0, fps))
        self._finish_open(db_ids, last_analysis, last_t)

    @staticmethod
    def _info(analysis: FrameAnalysis, now: float, wall0: datetime, fps: float) -> FrameInfo:
        rows = [
            ((wall0 + timedelta(seconds=a.confirmed_t)).strftime("%H:%M:%S"), f"#{a.track_id}", a.zone,
             KIND_LABELS[a.kind], f"{int(now - a.started_t)} с")
            for a in analysis.result.active
        ]
        persons = [p for p in analysis.result.persons if p.state != "ignored"]
        return FrameInfo(fps, len(persons), sum(1 for p in persons if p.state == "violation"), rows)

    def _finish_open(self, db_ids: dict[int, int], analysis: FrameAnalysis | None, last_t: float) -> None:
        """Нарушения, которые ещё длились при остановке, получают длительность на момент остановки."""
        if analysis is not None:
            for a in analysis.result.active:
                record_id = db_ids.get(a.uid)
                if record_id:
                    self.storage.set_duration(record_id, max(0.0, last_t - a.started_t))
        db_ids.clear()

    def _log_events(self, analysis: FrameAnalysis, frame: np.ndarray, wall0: datetime,
                    db_ids: dict[int, int]) -> None:
        for ev in analysis.result.new:
            ts = wall0 + timedelta(seconds=ev.t)
            shift = shift_for(ts, self.cfg.shifts)
            snapshot = self._save_snapshot(frame, analysis, ev, ts)
            record_id = self.storage.add(ts, shift.number, self.cfg.camera_name, ev.zone, ev.kind,
                                         track_id=ev.track_id, snapshot=snapshot)
            db_ids[ev.uid] = record_id
            self.violation_logged.emit(self.storage.get(record_id))
        for resolved in analysis.result.resolved:
            record_id = db_ids.pop(resolved.uid, None)
            if record_id:
                self.storage.set_duration(record_id, resolved.duration_s)

    def _save_snapshot(self, frame: np.ndarray, analysis: FrameAnalysis, ev: ViolationEvent,
                       ts: datetime) -> str | None:
        """Кадр как в окне мониторинга: у каждого человека подпись «#номер», нарушитель из записи обведён белым."""
        image = render_frame(frame, analysis, self.cfg.zones, highlight=ev.track_id)
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        if not image.save(buffer, "JPG", 88):
            return None
        folder = self.cfg.snapshots_dir / f"{ts:%Y-%m-%d}"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{ts:%H%M%S}_{ev.kind}_id{ev.track_id}.jpg"
        path.write_bytes(bytes(buffer.data()))  # через байты: пути с кириллицей на Windows безопасны
        try:
            return path.relative_to(self.cfg.root).as_posix()
        except ValueError:
            return str(path)
