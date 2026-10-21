"""Правила: привязка СИЗ к человеку, зоны и подтверждение нарушений по времени."""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Sequence

from .geometry import Box, box_area, box_center, intersection_area, point_in_polygon

# роль СИЗ -> тип нарушения, если СИЗ нет
KIND_BY_ROLE = {"helmet": "no_helmet", "vest": "no_vest"}
KIND_LABELS = {"no_helmet": "Нет каски", "no_vest": "Нет сигнального жилета"}


@dataclass(frozen=True)
class Detection:
    """Один объект от нейросети. role: person, helmet, vest, no_helmet, no_vest."""
    role: str
    conf: float
    box: Box


@dataclass(frozen=True)
class Zone:
    name: str
    polygon: tuple[tuple[float, float], ...]  # координаты в долях кадра, 0..1
    required: tuple[str, ...]  # обязательные СИЗ: helmet, vest

    def contains(self, x: float, y: float) -> bool:
        return point_in_polygon(x, y, self.polygon)


@dataclass(frozen=True)
class RulesParams:
    confirm_seconds: float = 3.0   # окно наблюдения: за это время СИЗ должно отсутствовать, чтобы зафиксировать нарушение
    clear_seconds: float = 2.0     # окно, в котором СИЗ должно быть видно, чтобы нарушение считалось устранённым
    violation_ratio: float = 0.8   # доля кадров окна confirm_seconds без СИЗ (нейросеть иногда «не видит» каску)
    resolve_ratio: float = 0.5     # доля кадров окна clear_seconds с СИЗ для признания нарушения устранённым
    min_person_height_frac: float = 0.12  # люди мельче этой доли высоты кадра не оцениваются
    dedup_seconds: float = 15.0    # окно защиты от дублей при смене номера трека
    dedup_distance_frac: float = 0.08     # расстояние (доля диагонали кадра) для той же защиты
    use_negative_classes: bool = True     # учитывать классы модели «нет каски / нет жилета»


@dataclass
class PersonStatus:
    track_id: int
    box: Box
    zone: str | None
    ppe: dict[str, bool]        # роль -> есть ли СИЗ (только обязательные в зоне)
    state: str                  # ignored | ok | warning | violation
    missing: list[str] = field(default_factory=list)  # подтверждённые нарушения (kind)


@dataclass
class ActiveViolation:
    uid: int
    kind: str
    zone: str
    track_id: int
    started_t: float
    confirmed_t: float
    box: Box


@dataclass
class ViolationEvent:
    uid: int
    kind: str
    zone: str
    track_id: int
    t: float
    started_t: float
    box: Box


@dataclass
class ResolvedEvent:
    uid: int
    duration_s: float


@dataclass
class StepResult:
    t: float
    persons: list[PersonStatus]
    active: list[ActiveViolation]
    new: list[ViolationEvent]
    resolved: list[ResolvedEvent]


def head_region(pb: Box) -> Box:
    w, h = pb[2] - pb[0], pb[3] - pb[1]
    return pb[0] - 0.15 * w, pb[1] - 0.15 * h, pb[2] + 0.15 * w, pb[1] + 0.40 * h


def torso_region(pb: Box) -> Box:
    w, h = pb[2] - pb[0], pb[3] - pb[1]
    return pb[0] - 0.10 * w, pb[1] + 0.15 * h, pb[2] + 0.10 * w, pb[1] + 0.75 * h


def _center_in(box: Box, region: Box) -> bool:
    cx, cy = box_center(box)
    return region[0] <= cx <= region[2] and region[1] <= cy <= region[3]


def _evidence(role: str, person_box: Box, dets: Sequence[Detection]) -> float:
    """Лучшая уверенность модели в том, что объект роли role принадлежит этому человеку."""
    region = head_region(person_box) if role in ("helmet", "no_helmet") else torso_region(person_box)
    best = 0.0
    for d in dets:
        if d.role != role or not _center_in(d.box, region):
            continue
        if role in ("vest", "no_vest"):
            area = box_area(d.box)
            if area <= 0 or intersection_area(d.box, person_box) / area < 0.5:
                continue
        best = max(best, d.conf)
    return best


def ppe_present(role: str, person_box: Box, dets: Sequence[Detection], use_negative: bool = True) -> bool:
    """Есть ли у человека СИЗ данной роли (helmet или vest)."""
    positive = _evidence(role, person_box, dets)
    negative = _evidence("no_" + role, person_box, dets) if use_negative else 0.0
    return positive > 0.0 and positive >= negative


class _State:
    """Состояние «человек X не имеет СИЗ Y»."""
    __slots__ = ("samples", "started_t", "last_bad", "last_seen", "uid", "confirmed_t",
                 "zone", "box", "track_id", "kind", "reported")

    def __init__(self, t: float, track_id: int, kind: str):
        self.samples: deque[tuple[float, bool]] = deque()  # (время, СИЗ есть) по последним кадрам
        self.started_t: float | None = None   # когда началось подтверждённое нарушение
        self.last_bad: float | None = None    # последний кадр без СИЗ
        self.last_seen = t
        self.uid: int | None = None
        self.confirmed_t: float | None = None
        self.zone = ""
        self.box: Box = (0, 0, 0, 0)
        self.track_id = track_id
        self.kind = kind
        self.reported = False

    def window(self, t: float, seconds: float) -> list[tuple[float, bool]]:
        return [s for s in self.samples if t - s[0] <= seconds]

    def missing_ratio(self, t: float, seconds: float) -> float:
        win = self.window(t, seconds)
        return sum(1 for _, ok in win if not ok) / len(win) if win else 0.0


class ViolationEngine:
    def __init__(self, zones: Sequence[Zone], params: RulesParams | None = None):
        self.zones = tuple(zones)
        self.params = params or RulesParams()
        self._states: dict[tuple[int, str], _State] = {}
        self._closed: list[tuple[float, str, str, tuple[float, float]]] = []
        self._next_uid = 1

    def reset(self) -> None:
        self._states.clear()
        self._closed.clear()

    def _zone_at(self, x: float, y: float) -> Zone | None:
        for zone in self.zones:
            if zone.contains(x, y):
                return zone
        return None

    def _close(self, key: tuple[int, str], st: _State, t: float, resolved: list[ResolvedEvent]) -> None:
        if st.uid is not None and st.started_t is not None and st.last_bad is not None:
            resolved.append(ResolvedEvent(st.uid, max(0.0, st.last_bad - st.started_t)))
            self._closed.append((t, st.kind, st.zone, box_center(st.box)))
        self._states.pop(key, None)

    def _is_duplicate(self, t: float, kind: str, zone: str, box: Box, diag: float) -> bool:
        """Тот же нарушитель под новым номером трека: рядом недавно закончился такой же эпизод."""
        p = self.params
        self._closed = [c for c in self._closed if t - c[0] <= p.dedup_seconds]
        cx, cy = box_center(box)
        return any(
            k == kind and z == zone and math.hypot(cx - c[0], cy - c[1]) <= p.dedup_distance_frac * diag
            for _, k, z, c in self._closed
        )

    def update(self, t: float, tracks: Sequence[tuple[int, Box]], dets: Sequence[Detection],
               frame_w: int, frame_h: int) -> StepResult:
        p = self.params
        diag = math.hypot(frame_w, frame_h)
        min_height = p.min_person_height_frac * frame_h
        statuses: list[PersonStatus] = []
        new: list[ViolationEvent] = []
        resolved: list[ResolvedEvent] = []
        seen: set[tuple[int, str]] = set()

        for track_id, pbox in tracks:
            zone = None
            if pbox[3] - pbox[1] >= min_height:
                fx = min(max((pbox[0] + pbox[2]) / 2.0 / frame_w, 0.001), 0.999)
                fy = min(max(pbox[3] / frame_h, 0.001), 0.999)  # точка опоры: низ рамки
                zone = self._zone_at(fx, fy)
            if zone is None:
                statuses.append(PersonStatus(track_id, pbox, None, {}, "ignored"))
                continue

            ppe: dict[str, bool] = {}
            for role in zone.required:
                kind = KIND_BY_ROLE[role]
                key = (track_id, kind)
                seen.add(key)
                present = ppe_present(role, pbox, dets, p.use_negative_classes)
                ppe[role] = present
                st = self._states.get(key)
                if st is None:
                    st = self._states[key] = _State(t, track_id, kind)
                st.last_seen, st.zone, st.box = t, zone.name, pbox

                st.samples.append((t, present))
                while st.samples and t - st.samples[0][0] > max(p.confirm_seconds, p.clear_seconds):
                    st.samples.popleft()
                if not present:
                    st.last_bad = t

                if st.uid is None:
                    # нейросеть иногда не видит каску, поэтому решает доля кадров окна, а не один кадр
                    win = st.window(t, p.confirm_seconds)
                    if (t - win[0][0] >= 0.9 * p.confirm_seconds
                            and st.missing_ratio(t, p.confirm_seconds) >= p.violation_ratio):
                        st.uid = self._next_uid
                        self._next_uid += 1
                        st.confirmed_t = t
                        st.started_t = next(ts for ts, ok in win if not ok)
                        if not self._is_duplicate(t, kind, zone.name, pbox, diag):
                            st.reported = True
                            new.append(ViolationEvent(st.uid, kind, zone.name, track_id, t, st.started_t, pbox))
                else:
                    win = st.window(t, p.clear_seconds)
                    ok_ratio = sum(1 for _, ok in win if ok) / len(win)
                    if t - win[0][0] >= 0.8 * p.clear_seconds and ok_ratio >= p.resolve_ratio:
                        self._close(key, st, t, resolved)

            missing = [k for (tid, k), s in self._states.items() if tid == track_id and s.uid is not None]
            warning = any(s.uid is None and s.missing_ratio(t, p.confirm_seconds) >= 0.5
                          for (tid, _), s in self._states.items() if tid == track_id)
            state = "violation" if missing else ("warning" if warning else "ok")
            statuses.append(PersonStatus(track_id, pbox, zone.name, ppe, state, missing))

        for key in list(self._states):
            if key not in seen and t - self._states[key].last_seen >= p.clear_seconds:
                self._close(key, self._states[key], t, resolved)

        active = sorted(
            (ActiveViolation(s.uid, s.kind, s.zone, s.track_id, s.started_t, s.confirmed_t, s.box)
             for s in self._states.values() if s.uid is not None),
            key=lambda a: a.started_t,
        )
        return StepResult(t, statuses, active, new, resolved)
