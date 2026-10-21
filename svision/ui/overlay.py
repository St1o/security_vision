"""Отрисовка зон, людей и СИЗ поверх кадра (Qt, чтобы подписи были на русском)."""
from __future__ import annotations

from typing import Sequence

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPainter, QPen, QPolygonF

from ..pipeline import FrameAnalysis
from ..rules import KIND_LABELS, Zone

STATE_COLORS = {
    "ok": QColor(46, 160, 67),
    "warning": QColor(234, 160, 10),
    "violation": QColor(220, 38, 38),
    "ignored": QColor(150, 150, 150),
}
PPE_COLOR = QColor(0, 180, 216)
NEGATIVE_COLOR = QColor(214, 51, 132)


def bgr_to_qimage(frame: np.ndarray) -> QImage:
    frame = np.ascontiguousarray(frame)
    height, width = frame.shape[:2]
    return QImage(frame.data, width, height, frame.strides[0], QImage.Format.Format_BGR888).copy()


def _label(painter: QPainter, text: str, x: float, y: float, color: QColor, font: QFont) -> None:
    painter.setFont(font)
    metrics = QFontMetricsF(font)
    width = metrics.horizontalAdvance(text) + 10
    height = metrics.height() + 4
    top = max(0.0, y - height)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawRect(QRectF(x, top, width, height))
    painter.setPen(QColor(255, 255, 255))
    painter.drawText(QPointF(x + 5, top + height - metrics.descent() - 2), text)


def render_frame(frame: np.ndarray, analysis: FrameAnalysis | None, zones: Sequence[Zone],
                 highlight: int | None = None) -> QImage:
    """highlight: номер человека, которого нужно выделить белой обводкой (для фото в журнале)."""
    image = bgr_to_qimage(frame)
    width, height = image.width(), image.height()
    k = max(width, height) / 1000.0  # масштаб линий и шрифта под размер кадра
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    font = QFont()
    font.setPixelSize(max(12, int(15 * k)))
    font.setBold(True)

    for zone in zones:
        polygon = QPolygonF([QPointF(x * width, y * height) for x, y in zone.polygon])
        pen = QPen(QColor(255, 255, 255, 190), max(1.5, 2 * k), Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPolygon(polygon)
        bounds = polygon.boundingRect()
        _label(painter, zone.name, bounds.left() + 6 * k, bounds.top() + 28 * k, QColor(40, 40, 40, 200), font)

    if analysis is not None:
        for det in analysis.detections:
            if det.role == "person":
                continue
            color = NEGATIVE_COLOR if det.role.startswith("no_") else PPE_COLOR
            painter.setPen(QPen(color, max(1.0, 1.5 * k)))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            x1, y1, x2, y2 = det.box
            painter.drawRect(QRectF(x1, y1, x2 - x1, y2 - y1))

        for person in analysis.result.persons:
            x1, y1, x2, y2 = person.box
            color = STATE_COLORS[person.state]
            if person.track_id == highlight:
                margin = 4 * k
                painter.setPen(QPen(QColor(255, 255, 255), max(3.0, 6 * k)))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(QRectF(x1 - margin, y1 - margin, x2 - x1 + 2 * margin, y2 - y1 + 2 * margin))
            painter.setPen(QPen(color, max(1.5, (3 if person.state != "ignored" else 1.5) * k)))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(QRectF(x1, y1, x2 - x1, y2 - y1))
            if person.state == "ignored":
                continue
            if person.state == "violation":
                text = f"#{person.track_id}  " + ", ".join(KIND_LABELS[m].lower() for m in person.missing)
            elif person.state == "warning":
                text = f"#{person.track_id}  проверка СИЗ…"
            else:
                text = f"#{person.track_id}  СИЗ в норме"
            _label(painter, text, x1, y1, color, font)

    painter.end()
    return image
