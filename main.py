"""Запуск: python main.py [--config config/default.json] [--source путь_к_видео | номер_камеры | rtsp://...]"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from svision.config import ConfigError, PROJECT_ROOT, load_config
from svision.storage import Storage
from svision.ui.main_window import MainWindow


def main() -> int:
    parser = argparse.ArgumentParser(description="Security Vision: контроль каски и сигнального жилета")
    parser.add_argument("--config", default=str(PROJECT_ROOT / "config" / "default.json"))
    parser.add_argument("--source", help="видеофайл, номер веб-камеры или RTSP-адрес (по умолчанию из конфига)")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    try:
        cfg = load_config(Path(args.config))
    except ConfigError as exc:
        QMessageBox.critical(None, "Ошибка конфигурации", str(exc))
        return 1

    source = None
    if args.source is not None:
        source = int(args.source) if args.source.isdigit() else args.source

    storage = Storage(cfg.db_path, base_dir=cfg.root)
    storage.init()
    window = MainWindow(cfg, storage, source)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
