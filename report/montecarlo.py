"""Оценка устойчивости правила подтверждения нарушений моделированием (метод Монте-Карло).

Запускается настоящий код svision/rules.py на искусственных последовательностях обнаружений:
кадры считаются независимыми, частота 10 кадров/с. Результаты используются в разделе 3.2 отчёта.

    python report/montecarlo.py
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from svision.rules import Detection, RulesParams, ViolationEngine, Zone  # noqa: E402

ZONE = Zone("A", ((0, 0), (1, 0), (1, 1), (0, 1)), ("helmet", "vest"))
PERSON = (400.0, 300.0, 500.0, 600.0)
VEST = Detection("vest", 0.9, (410.0, 380.0, 490.0, 470.0))
HELMET = Detection("helmet", 0.9, (420.0, 300.0, 480.0, 340.0))
RUNS = 1000


def first_violation(p_helmet_found: float, seconds: float, seed: int, fps: int = 10):
    """Время первой фиксации нарушения «нет каски» или None."""
    rng = random.Random(seed)
    engine = ViolationEngine([ZONE], RulesParams())
    for i in range(int(seconds * fps) + 1):
        dets = [VEST] + ([HELMET] if rng.random() < p_helmet_found else [])
        result = engine.update(i / fps, [(1, PERSON)], dets, 1000, 1000)
        if any(e.kind == "no_helmet" for e in result.new):
            return i / fps
    return None


if __name__ == "__main__":
    print("Работник в каске: ложные фиксации за 60 с")
    for p_miss in (0.25, 0.31):
        bad = sum(first_violation(1 - p_miss, 60, s) is not None for s in range(RUNS))
        print(f"  пропуск каски {p_miss:.2f}: {bad} из {RUNS}")
    print("Работник без каски (ложное обнаружение каски 0,17): доля зафиксированных нарушений к моменту T")
    times = [first_violation(0.17, 12, s) for s in range(RUNS)]
    for limit in (4, 6, 8, 12):
        ok = sum(t is not None and t <= limit for t in times)
        print(f"  T = {limit:>2} с: {ok / RUNS:.3f}")
    found = sorted(t for t in times if t is not None)
    print("  медиана времени фиксации, с:", found[len(found) // 2])
