"""Рабочие смены (по умолчанию три по 8 часов)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import Sequence


def parse_hhmm(text: str) -> int:
    """'08:30' -> минуты от начала суток; допускается '24:00'."""
    try:
        hours, minutes = text.strip().split(":")
        total = int(hours) * 60 + int(minutes)
    except ValueError:
        raise ValueError(f"Неверный формат времени: {text!r}, ожидается ЧЧ:ММ") from None
    if not 0 <= total <= 1440:
        raise ValueError(f"Время вне суток: {text!r}")
    return total


def format_minutes(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


@dataclass(frozen=True)
class Shift:
    number: int
    name: str
    start_min: int
    end_min: int

    @property
    def label(self) -> str:
        return f"{format_minutes(self.start_min)}–{format_minutes(self.end_min)}"

    def contains(self, minute: int) -> bool:
        if self.start_min < self.end_min:
            return self.start_min <= minute < self.end_min
        return minute >= self.start_min or minute < self.end_min  # смена через полночь


def validate_shifts(shifts: Sequence[Shift]) -> None:
    """Каждая минута суток должна принадлежать ровно одной смене."""
    if not shifts:
        raise ValueError("Не задано ни одной смены")
    numbers = [s.number for s in shifts]
    if len(set(numbers)) != len(numbers):
        raise ValueError("Номера смен повторяются")
    for minute in range(1440):
        count = sum(1 for s in shifts if s.contains(minute))
        if count != 1:
            raise ValueError(
                f"Смены должны покрывать сутки без пропусков и пересечений "
                f"(проблема в {format_minutes(minute)})"
            )


def shift_for(moment: datetime | time, shifts: Sequence[Shift]) -> Shift:
    minute = moment.hour * 60 + moment.minute
    for shift in shifts:
        if shift.contains(minute):
            return shift
    raise ValueError("Момент времени не попадает ни в одну смену")
