"""Заполняет журнал ТЕСТОВЫМИ записями за прошедшие дни, чтобы показать календарь и акты.

Записи помечаются is_demo=1: в таблицах пишется «тестовая запись», в акте стоит предупреждение.
Реальные нарушения (из видео) этим скриптом не создаются и не удаляются.

    python tools/seed_demo_data.py --clear          # заменить старые тестовые записи новыми
    python tools/seed_demo_data.py --days 30 --count 7 --seed 7
"""
from __future__ import annotations

import argparse
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from svision.config import PROJECT_ROOT, load_config  # noqa: E402
from svision.rules import KIND_BY_ROLE  # noqa: E402
from svision.storage import Storage  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(PROJECT_ROOT / "config" / "default.json"))
    parser.add_argument("--days", type=int, default=30, help="за сколько прошедших дней")
    parser.add_argument("--count", type=int, default=7, help="сколько дней с нарушениями")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--clear", action="store_true", help="сначала удалить прежние тестовые записи")
    args = parser.parse_args()

    cfg = load_config(args.config)
    storage = Storage(cfg.db_path, base_dir=cfg.root)
    storage.init()
    if args.clear:
        print("Удалено прежних тестовых записей:", storage.delete_demo())

    rng = random.Random(args.seed)
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    days = rng.sample(range(1, args.days + 1), min(args.count, args.days))  # сегодня не трогаем
    kinds = sorted(KIND_BY_ROLE.values())
    total = 0
    for offset in sorted(days, reverse=True):
        day = today - timedelta(days=offset)
        for shift in rng.sample(cfg.shifts, rng.choice([1, 1, 2])):
            for _ in range(rng.randint(1, 4)):
                minute = rng.randrange(shift.start_min, min(shift.end_min, 1440))
                ts = day + timedelta(minutes=minute, seconds=rng.randrange(60))
                zone = rng.choice(cfg.zones)
                storage.add(ts, shift.number, cfg.camera_name, zone.name, rng.choice(kinds),
                            track_id=rng.randint(1, 40), duration_s=float(rng.randint(3, 60)), is_demo=True)
                total += 1
    print(f"Создано тестовых записей: {total} за {len(days)} дн. Файл: {cfg.db_path}")


if __name__ == "__main__":
    main()
