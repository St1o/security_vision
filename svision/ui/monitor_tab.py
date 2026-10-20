"""Вкладка «Мониторинг»: видео с разметкой и таблица текущих нарушений."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QImage, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QPushButton,
                               QSizePolicy, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from .worker import FrameInfo

COLUMNS = ["Время", "Человек", "Зона", "Нарушение", "Длит."]


class VideoView(QLabel):
    def __init__(self):
        super().__init__("Нажмите «Старт», чтобы начать контроль")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(640, 400)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.setStyleSheet("background:#111; color:#9aa0a6; font-size:16px;")
        self._image: QImage | None = None

    def set_image(self, image: QImage) -> None:
        self._image = image
        self._redraw()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._redraw()

    def _redraw(self) -> None:
        if self._image is not None:
            self.setPixmap(QPixmap.fromImage(self._image).scaled(
                self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))


class MonitorTab(QWidget):
    start_clicked = Signal()
    stop_clicked = Signal()
    open_clicked = Signal()
    export_clicked = Signal()

    def __init__(self):
        super().__init__()
        self.start_btn = QPushButton("▶  Старт")
        self.stop_btn = QPushButton("■  Стоп")
        self.open_btn = QPushButton("Открыть видео…")
        self.source_label = QLabel()
        self.shift_label = QLabel()
        self.shift_label.setStyleSheet("font-weight:600;")
        self.status_label = QLabel("Остановлено")
        self.stats_label = QLabel("Людей в кадре: —   Нарушителей: —   Скорость: —")
        self.video = VideoView()
        self.table = QTableWidget(0, len(COLUMNS))
        self.export_btn = QPushButton("Выгрузить акт за текущую смену…")

        self.start_btn.clicked.connect(self.start_clicked)
        self.stop_btn.clicked.connect(self.stop_clicked)
        self.open_btn.clicked.connect(self.open_clicked)
        self.export_btn.clicked.connect(self.export_clicked)
        self.set_running(False)

        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        top = QHBoxLayout()
        for widget in (self.start_btn, self.stop_btn, self.open_btn):
            top.addWidget(widget)
        top.addSpacing(12)
        top.addWidget(self.source_label, 1)
        top.addWidget(self.shift_label)

        box = QGroupBox("Текущие нарушения")
        box_layout = QVBoxLayout(box)
        box_layout.addWidget(self.table, 1)
        box_layout.addWidget(self.stats_label)
        box_layout.addWidget(self.export_btn)
        box.setMinimumWidth(420)

        middle = QHBoxLayout()
        middle.addWidget(self.video, 3)
        middle.addWidget(box, 1)

        root = QVBoxLayout(self)
        root.addLayout(top)
        root.addLayout(middle, 1)
        root.addWidget(self.status_label)

    def set_running(self, running: bool) -> None:
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        self.open_btn.setEnabled(not running)

    def set_source_text(self, text: str) -> None:
        self.source_label.setText(f"Источник: {text}")

    def set_shift_text(self, text: str) -> None:
        self.shift_label.setText(text)

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def show_frame(self, image: QImage, info: FrameInfo) -> None:
        self.video.set_image(image)
        self.stats_label.setText(
            f"Людей в кадре: {info.persons}   Нарушителей: {info.violators}   Скорость: {info.fps:.1f} кадр/с")
        current = [tuple(self.table.item(r, c).text() for c in range(len(COLUMNS))) for r in range(self.table.rowCount())]
        if current != info.rows:
            self._fill(info.rows)

    def clear(self) -> None:
        self._fill([])
        self.stats_label.setText("Людей в кадре: —   Нарушителей: —   Скорость: —")

    def _fill(self, rows) -> None:
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, text in enumerate(row):
                item = QTableWidgetItem(text)
                item.setBackground(QColor(254, 226, 226))
                self.table.setItem(r, c, item)
