"""Конвейер обработки кадра: нейросеть -> трекинг -> правила."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

import numpy as np

from .rules import Detection, StepResult, ViolationEngine
from .tracking import IoUTracker


class Detector(Protocol):
    def detect(self, frame: np.ndarray) -> Sequence[Detection]: ...


@dataclass
class FrameAnalysis:
    detections: list[Detection]
    result: StepResult
    frame_size: tuple[int, int]  # (ширина, высота)


class Pipeline:
    def __init__(self, detector: Detector, tracker: IoUTracker, engine: ViolationEngine):
        self.detector = detector
        self.tracker = tracker
        self.engine = engine

    def reset(self) -> None:
        self.tracker.reset()
        self.engine.reset()

    def process(self, frame: np.ndarray, t: float) -> FrameAnalysis:
        height, width = frame.shape[:2]
        dets = list(self.detector.detect(frame))
        tracks = self.tracker.update([d.box for d in dets if d.role == "person"])
        result = self.engine.update(t, tracks, dets, width, height)
        return FrameAnalysis(dets, result, (width, height))
