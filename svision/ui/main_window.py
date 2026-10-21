"""Главное окно: вкладки «Мониторинг» и «Журнал», запуск обработки, выгрузка актов."""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox, QTabWidget

from ..config import AppConfig
from ..detector import YoloDetector
from ..pipeline import Detector
from ..report import build_act
from ..shifts import shift_for
from ..storage import Storage
from .journal_tab import JournalTab
from .monitor_tab import MonitorTab
from .worker import VideoWorker

VIDEO_FILTER = "Видео (*.mp4 *.avi *.mov *.mkv *.webm);;Все файлы (*)"


class MainWindow(QMainWindow):
    def __init__(self, cfg: AppConfig, storage: Storage, source: str | int | None = None,
                 detector_factory: Callable[[], Detector] | None = None):
        super().__init__()
        self.cfg = cfg
        self.storage = storage
        self.source = cfg.source if source is None else source
        self.detector_factory = detector_factory or self._yolo_factory
        self.worker: VideoWorker | None = None

        self.setWindowTitle("Security Vision — контроль применения СИЗ")
        available = QGuiApplication.primaryScreen().availableGeometry()  # чтобы окно не уходило под панель задач
        self.resize(min(1380, int(available.width() * 0.92)), min(820, int(available.height() * 0.86)))

        self.monitor = MonitorTab()
        self.journal = JournalTab(storage, cfg.shifts)
        tabs = QTabWidget()
        tabs.addTab(self.monitor, "Мониторинг")
        tabs.addTab(self.journal, "Журнал нарушений")
        tabs.currentChanged.connect(lambda _: self.journal.refresh())
        self.tabs = tabs
        self.setCentralWidget(tabs)

        self.monitor.set_source_text(self._source_text())
        self.monitor.start_clicked.connect(self.start)
        self.monitor.stop_clicked.connect(self.stop)
        self.monitor.open_clicked.connect(self.open_video)
        self.monitor.export_clicked.connect(self._export_current_shift)
        self.journal.export_requested.connect(self.export_act)

        self.clock = QTimer(self)
        self.clock.timeout.connect(self._tick)
        self.clock.start(1000)
        self._tick()

    def _yolo_factory(self) -> Detector:
        m = self.cfg.model
        return YoloDetector(m.path, m.imgsz, m.conf, m.device, m.class_map, self.cfg.required_roles)

    def _source_text(self) -> str:
        return f"камера {self.source}" if isinstance(self.source, int) else Path(self.source).name or str(self.source)

    def _tick(self) -> None:
        now = datetime.now()
        shift = shift_for(now, self.cfg.shifts)
        self.monitor.set_shift_text(f"Текущая смена: {shift.name} ({shift.label})  ·  {now:%d.%m.%Y %H:%M:%S}")

    # --- запуск и остановка ---------------------------------------------------------------

    def start(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            return
        source = self.source
        if isinstance(source, str) and "://" not in source and not Path(source).exists():
            QMessageBox.warning(self, "Видео не найдено",
                                f"Файл не найден:\n{source}\n\nВыберите видео кнопкой «Открыть видео…» "
                                "или положите файл в data/videos/site.mp4.")
            return
        self.monitor.clear()
        self.worker = VideoWorker(self.cfg, self.storage, source, self.detector_factory, parent=self)
        self.worker.frame_ready.connect(self.monitor.show_frame)
        self.worker.violation_logged.connect(self._on_violation)
        self.worker.status.connect(self.monitor.set_status)
        self.worker.failed.connect(self._on_failed)
        self.worker.finished.connect(self._on_finished)
        self.monitor.set_running(True)
        self.worker.start()

    def stop(self) -> None:
        if self.worker is not None:
            self.worker.stop()
            self.worker.wait(5000)

    def open_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Выберите видео", str(self.cfg.root / "data" / "videos"), VIDEO_FILTER)
        if path:
            self.source = path
            self.monitor.set_source_text(self._source_text())

    def _on_violation(self, record) -> None:
        self.monitor.set_status(f"Зафиксировано нарушение: {record.label} ({record.ts:%H:%M:%S})")
        self.journal.refresh()

    def _on_failed(self, message: str) -> None:
        QMessageBox.critical(self, "Ошибка", message)
        self.monitor.set_status("Ошибка: " + message.splitlines()[0][:120])

    def _on_finished(self) -> None:
        self.monitor.set_running(False)
        if self.monitor.status_label.text() in ("Идёт контроль", "Загрузка модели…"):
            self.monitor.set_status("Остановлено")
        self.journal.refresh()

    def closeEvent(self, event) -> None:
        self.stop()
        super().closeEvent(event)

    # --- акты -----------------------------------------------------------------------------

    def _export_current_shift(self) -> None:
        now = datetime.now()
        self.export_act(now.date(), shift_for(now, self.cfg.shifts).number)

    def export_act(self, day: date, shift_number: int) -> None:
        shift = next(s for s in self.cfg.shifts if s.number == shift_number)
        records = self.storage.list(day, shift_number)
        if not records:
            QMessageBox.information(self, "Выгрузка акта", "За выбранную смену нарушений нет.")
            return
        self.cfg.exports_dir.mkdir(parents=True, exist_ok=True)
        default = self.cfg.exports_dir / f"Акт_{day:%Y-%m-%d}_смена{shift_number}.docx"
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить акт", str(default), "Документ Word (*.docx)")
        if not path:
            return
        try:
            build_act(Path(path), records, day, shift, self.cfg.camera_name, self.cfg.object_name,
                      self.cfg.legal_basis, self.storage.snapshot_path)
        except OSError as exc:
            QMessageBox.warning(self, "Не удалось сохранить акт",
                                f"{exc}\n\nВозможно, файл открыт в Word. Закройте его и повторите.")
            return
        QMessageBox.information(self, "Акт сохранён", f"Акт сформирован:\n{path}")
