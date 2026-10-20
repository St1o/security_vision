"""Вкладка «Журнал»: календарь с отмеченными датами -> смены -> таблица нарушений -> акт."""
from __future__ import annotations

from datetime import date, datetime
from typing import Sequence

from PySide6.QtCore import QDate, QLocale, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPixmap, QTextCharFormat
from PySide6.QtWidgets import (QAbstractItemView, QButtonGroup, QCalendarWidget, QGroupBox, QHBoxLayout, QHeaderView,
                               QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from ..shifts import Shift
from ..storage import Storage, ViolationRecord

COLUMNS = ["№", "Время", "Зона", "Нарушение", "ID", "Длит., с", "Примечание"]


def _shift_style(has_violations: bool) -> str:
    bg, border = ("#fde2e2", "#dc2626") if has_violations else ("#e8f5e9", "#2e7d32")
    return (f"QPushButton {{ background:{bg}; border:2px solid {border}; border-radius:6px; "
            f"padding:8px; text-align:left; color:#202124; }} "
            f"QPushButton:checked {{ border:4px solid {border}; font-weight:bold; }}")


class JournalTab(QWidget):
    export_requested = Signal(object, int)  # дата, номер смены

    def __init__(self, storage: Storage, shifts: Sequence[Shift]):
        super().__init__()
        self.storage = storage
        self.shifts = tuple(shifts)
        self._records: list[ViolationRecord] = []
        self._selected_shift = self.shifts[0].number

        self.calendar = QCalendarWidget()
        self.calendar.setLocale(QLocale(QLocale.Language.Russian))
        self.calendar.setFirstDayOfWeek(Qt.DayOfWeek.Monday)
        self.calendar.setGridVisible(True)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        plain = QTextCharFormat()
        plain.setForeground(QBrush(QColor("#202124")))
        for day in (Qt.DayOfWeek.Saturday, Qt.DayOfWeek.Sunday):
            self.calendar.setWeekdayTextFormat(day, plain)  # красный текст выходных не путаем с нарушениями
        self.calendar.selectionChanged.connect(self._on_date_changed)
        self.calendar.currentPageChanged.connect(lambda y, m: self._highlight(y, m))

        legend = QLabel("Красным отмечены даты, в которые были нарушения. Выберите дату и смену, чтобы открыть список.")
        legend.setWordWrap(True)

        self.title = QLabel()
        self.title.setStyleSheet("font-size:16px; font-weight:600;")
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.shift_buttons: dict[int, QPushButton] = {}
        shifts_row = QHBoxLayout()
        for shift in self.shifts:
            button = QPushButton()
            button.setCheckable(True)
            button.setMinimumHeight(76)
            button.clicked.connect(lambda _=False, n=shift.number: self._select_shift(n))
            self.group.addButton(button)
            self.shift_buttons[shift.number] = button
            shifts_row.addWidget(button)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.itemSelectionChanged.connect(self._show_snapshot)

        self.preview = QLabel("Выберите нарушение, чтобы увидеть фото")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumHeight(190)
        self.preview.setStyleSheet("background:#f1f3f4; color:#5f6368;")

        self.export_btn = QPushButton("Выгрузить акт нарушений…")
        self.export_btn.clicked.connect(lambda: self.export_requested.emit(self.selected_date(), self._selected_shift))

        left = QVBoxLayout()
        left.addWidget(self.calendar)
        left.addWidget(legend)

        table_box = QGroupBox("Нарушения за выбранную смену")
        table_layout = QVBoxLayout(table_box)
        table_layout.addWidget(self.table, 1)
        table_layout.addWidget(self.preview)
        table_layout.addWidget(self.export_btn)

        right = QVBoxLayout()
        right.addWidget(self.title)
        right.addLayout(shifts_row)
        right.addWidget(table_box, 1)

        root = QHBoxLayout(self)
        root.addLayout(left, 2)
        root.addLayout(right, 3)

        today = QDate.currentDate()
        self.calendar.setSelectedDate(today)
        self.refresh()

    def selected_date(self) -> date:
        d = self.calendar.selectedDate()
        return date(d.year(), d.month(), d.day())

    def refresh(self) -> None:
        self._highlight(self.calendar.yearShown(), self.calendar.monthShown())
        self._on_date_changed()

    def _highlight(self, year: int, month: int) -> None:
        self.calendar.setDateTextFormat(QDate(), QTextCharFormat())  # сбросить старую подсветку
        fmt = QTextCharFormat()
        fmt.setBackground(QBrush(QColor(252, 165, 165)))  # сплошная заливка: одинаково читается на любой ОС
        fmt.setForeground(QBrush(QColor(127, 29, 29)))
        fmt.setFontWeight(QFont.Weight.Bold)
        for offset in (-1, 0, 1):  # соседние месяцы тоже видны в сетке календаря
            y, m = year, month + offset
            if m < 1:
                y, m = y - 1, 12
            elif m > 12:
                y, m = y + 1, 1
            for d in self.storage.days_with_violations(y, m):
                self.calendar.setDateTextFormat(QDate(d.year, d.month, d.day), fmt)

    def _on_date_changed(self) -> None:
        day = self.selected_date()
        self.title.setText(f"Дата: {day:%d.%m.%Y}")
        counts = self.storage.counts_by_shift(day)
        for shift in self.shifts:
            n = counts.get(shift.number, 0)
            button = self.shift_buttons[shift.number]
            button.setText(f"{shift.name}\n{shift.label}\n" + (f"нарушений: {n}" if n else "нарушений нет"))
            button.setStyleSheet(_shift_style(n > 0))
        busy = [s.number for s in self.shifts if counts.get(s.number, 0)]
        if self._selected_shift not in busy and busy:
            self._selected_shift = busy[0]  # сразу открываем смену с нарушениями
        self._select_shift(self._selected_shift)

    def _select_shift(self, number: int) -> None:
        self._selected_shift = number
        self.shift_buttons[number].setChecked(True)
        self._records = self.storage.list(self.selected_date(), number)
        self.table.setRowCount(len(self._records))
        for r, rec in enumerate(self._records):
            values = [str(r + 1), rec.ts.strftime("%H:%M:%S"), rec.zone, rec.label,
                      str(rec.track_id) if rec.track_id is not None else "—",
                      f"{rec.duration_s:.0f}" if rec.duration_s is not None else "—",
                      "тестовая запись" if rec.is_demo else ""]
            for c, text in enumerate(values):
                item = QTableWidgetItem(text)
                item.setBackground(QColor(254, 226, 226))
                self.table.setItem(r, c, item)
        self.export_btn.setEnabled(bool(self._records))
        self.preview.setPixmap(QPixmap())
        self.preview.setText("Выберите нарушение, чтобы увидеть фото" if self._records else "В эту смену нарушений нет")

    def _show_snapshot(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        rec = self._records[rows[0].row()]
        path = self.storage.snapshot_path(rec)
        if path is None:
            self.preview.setPixmap(QPixmap())
            self.preview.setText("Фото для этой записи нет")
            return
        pixmap = QPixmap(str(path))
        self.preview.setPixmap(pixmap.scaled(self.preview.width(), self.preview.height(),
                                             Qt.AspectRatioMode.KeepAspectRatio,
                                             Qt.TransformationMode.SmoothTransformation))
