"""Простой трекер людей: сопоставление рамок между кадрами по IoU.

Нужен, чтобы «человек №3» оставался одним и тем же человеком от кадра к кадру
и нарушение считалось по времени, а не по одному случайному кадру.
Ограничение: если человека надолго закрыл другой объект, трек может смениться.
От дублей из-за этого защищает дедупликация в rules.py.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .geometry import Box, iou


@dataclass(frozen=True)
class TrackerParams:
    iou_threshold: float = 0.3
    max_missed: int = 8
    min_hits: int = 2


class _Track:
    __slots__ = ("id", "box", "hits", "missed")

    def __init__(self, track_id: int, box: Box):
        self.id = track_id
        self.box = box
        self.hits = 1
        self.missed = 0


class IoUTracker:
    def __init__(self, params: TrackerParams | None = None):
        self.params = params or TrackerParams()
        self._tracks: list[_Track] = []
        self._next_id = 1

    def reset(self) -> None:
        self._tracks.clear()
        self._next_id = 1

    def update(self, boxes: Sequence[Box]) -> list[tuple[int, Box]]:
        """Принимает рамки людей текущего кадра, возвращает [(id, рамка)] подтверждённых треков."""
        p = self.params
        pairs = []
        for ti, track in enumerate(self._tracks):
            for bi, box in enumerate(boxes):
                score = iou(track.box, box)
                if score >= p.iou_threshold:
                    pairs.append((score, ti, bi))
        pairs.sort(reverse=True)

        used_tracks: set[int] = set()
        used_boxes: set[int] = set()
        for _, ti, bi in pairs:
            if ti in used_tracks or bi in used_boxes:
                continue
            track = self._tracks[ti]
            track.box = boxes[bi]
            track.hits += 1
            track.missed = 0
            used_tracks.add(ti)
            used_boxes.add(bi)

        for ti, track in enumerate(self._tracks):
            if ti not in used_tracks:
                track.missed += 1
        self._tracks = [t for t in self._tracks if t.missed <= p.max_missed]

        for bi, box in enumerate(boxes):
            if bi not in used_boxes:
                self._tracks.append(_Track(self._next_id, box))
                self._next_id += 1

        return [(t.id, t.box) for t in self._tracks if t.missed == 0 and t.hits >= p.min_hits]
