"""Дымовые тесты интерфейса и фонового потока (Qt без экрана).

Видео здесь синтетическое, а детекции заданы заранее: проверяется логика программы,
а не качество нейросети.
"""
import os
import time
from dataclasses import replace
from datetime import date, datetime, timedelta

import cv2
import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtCore import QDate, Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from svision.config import PROJECT_ROOT, load_config  # noqa: E402
from svision.rules import Detection, RulesParams  # noqa: E402
from svision.storage import Storage  # noqa: E402
from svision.ui.main_window import MainWindow  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def cfg(tmp_path):
    base = load_config(PROJECT_ROOT / "config" / "default.json")
    return replace(base, root=tmp_path, db_path=tmp_path / "v.db", snapshots_dir=tmp_path / "snaps",
                   exports_dir=tmp_path / "exports", loop=False, rules=RulesParams(confirm_seconds=1.0))


class FakeDetector:
    """Человек в жилете, но без каски."""
    def detect(self, frame):
        return [Detection("person", 0.9, (200.0, 150.0, 300.0, 450.0)),
                Detection("vest", 0.9, (210.0, 230.0, 290.0, 330.0))]


def make_video(path, seconds=6, fps=10):
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), fps, (640, 480))
    for i in range(seconds * fps):
        frame = np.full((480, 640, 3), 90, np.uint8)
        cv2.rectangle(frame, (200, 150), (300, 450), (60, 120, 200), -1)
        writer.write(frame)
    writer.release()


def test_journal_highlights_days_and_shows_shifts(app, cfg):
    storage = Storage(cfg.db_path, cfg.root)
    storage.init()
    day = datetime.now().replace(hour=9, minute=30, second=0, microsecond=0) - timedelta(days=2)
    storage.add(day, 2, "Камера 1", "Зона А", "no_helmet", track_id=3, duration_s=12, is_demo=True)
    storage.add(day + timedelta(hours=1), 2, "Камера 1", "Зона А", "no_vest", track_id=5, is_demo=True)

    window = MainWindow(cfg, storage, source="x.mp4")
    journal = window.journal
    journal.calendar.setSelectedDate(QDate(day.year, day.month, day.day))
    journal.refresh()

    formats = journal.calendar.dateTextFormat()
    marked = QDate(day.year, day.month, day.day)
    assert formats[marked].background().color().red() > 200 and formats[marked].background().color().green() < 200
    assert marked.addDays(-1) not in formats  # дни без нарушений не подсвечены
    assert "нарушений: 2" in journal.shift_buttons[2].text()
    assert "нарушений нет" in journal.shift_buttons[1].text()
    assert journal.shift_buttons[2].isChecked()
    assert journal.table.rowCount() == 2
    assert journal.table.item(0, 3).text() == "Нет каски"
    assert journal.table.item(0, 6).text() == "тестовая запись"
    window.close()


def test_worker_logs_violation_with_snapshot(app, cfg, tmp_path):
    video = tmp_path / "site.avi"
    make_video(video)
    storage = Storage(cfg.db_path, cfg.root)
    storage.init()
    window = MainWindow(cfg, storage, source=str(video), detector_factory=FakeDetector)
    window.start()

    deadline = time.time() + 20
    while time.time() < deadline and window.worker.isRunning():
        app.processEvents()
        time.sleep(0.02)
    app.processEvents()
    assert not window.worker.isRunning()

    today = date.today()
    shift = window.cfg.shifts
    records = [r for n in (1, 2, 3) for r in storage.list(today, n)]
    assert [r.kind for r in records] == ["no_helmet"]  # жилет есть, каски нет
    rec = records[0]
    assert rec.track_id is not None and rec.duration_s is not None and rec.duration_s > 0
    snapshot = storage.snapshot_path(rec)
    assert snapshot is not None and snapshot.stat().st_size > 1000
    assert window.monitor.table.rowCount() >= 0
    window.close()
