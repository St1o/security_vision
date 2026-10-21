"""Схемы и графики для отчёта. Запуск: python report/make_figures.py

Рисунок с моделированием (fig_window.png) считается настоящим кодом программы (svision/rules.py)
на искусственной последовательности обнаружений, это не результат наблюдений на стройплощадке.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(exist_ok=True)

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.unicode_minus": False})
GRAY, DARK, LIGHT = "#d9d9d9", "#222222", "#f2f2f2"


def box(ax, x, y, w, h, text, fc=LIGHT, fs=9.5, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12", fc=fc, ec=DARK, lw=1.2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal", wrap=True)


def arrow(ax, x1, y1, x2, y2, text=None, dx=0.0, dy=0.0):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=14, lw=1.2, color=DARK))
    if text:
        ax.text((x1 + x2) / 2 + dx, (y1 + y2) / 2 + dy, text, fontsize=9, ha="center", va="center")


def fig_timeline():
    events = [
        (1942, "1942\nпервая система\nзамкнутого ТВ\n(Пенемюнде)", 1),
        (1949, "1949\nпервая\nкоммерческая\nсистема Vericon", -1),
        (2001, "2001\nметод\nВиолы–Джонса", 1),
        (2005, "2005\nHOG + SVM", -1),
        (2012, "2012\nAlexNet:\nглубокие сети", 1),
        (2016, "2016\nYOLO:\nдетекция в\nреальном времени", -1),
        (2018, "2018\nдетекция касок\nглубокой сетью\n(Fang и др.)", 1),
        (2019, "2019\nнабор данных\nдля касок\n(Wu и др.)", -1),
        (2021, "2021\nсистемы контроля СИЗ\nна промышленных\nпредприятиях РФ", 1),
        (2024, "2024\nYOLO11;\nнабор данных SH17", -1),
    ]
    fig, ax = plt.subplots(figsize=(11, 4.2))
    ax.axhline(0, color=DARK, lw=2)
    pos = {2: None}
    xs = list(range(len(events)))
    for i, (year, label, side) in zip(xs, events):
        ax.plot([i], [0], "o", color=DARK, ms=7)
        ax.plot([i, i], [0, side * 0.55], color=DARK, lw=1)
        ax.text(i, side * 0.62, label, ha="center", va="bottom" if side > 0 else "top", fontsize=8.6)
    ax.set_xlim(-0.7, len(events) - 0.3)
    ax.set_ylim(-1.7, 1.7)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(OUT / "fig_timeline.png", dpi=200)
    plt.close(fig)


def fig_algorithm():
    fig, ax = plt.subplots(figsize=(8.2, 10.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(-1.2, 20)
    ax.axis("off")
    steps = [
        (17.6, "Видеопоток\n(файл, веб-камера, RTSP)"),
        (15.1, "Обнаружение объектов нейросетью YOLO11n:\nчеловек, каска, жилет"),
        (12.6, "Трекинг людей по пересечению рамок (IoU):\nпостоянный номер «#ID» на каждого человека"),
        (10.1, "Определение зоны контроля\nпо точке опоры человека (низ рамки)"),
        (7.6, "Привязка СИЗ к человеку:\nкаска — в области головы, жилет — на торсе"),
        (5.1, "Окно подтверждения (3 с):\nСИЗ отсутствует не менее чем в 80% кадров?"),
    ]
    for y, text in steps[:-1]:
        box(ax, 1.5, y, 7, 1.7, text)
    # ромб для решения
    y, text = steps[-1]
    ax.add_patch(Polygon([[5, y + 2.0], [9.2, y + 0.85], [5, y - 0.3], [0.8, y + 0.85]], closed=True, fc=GRAY, ec=DARK, lw=1.2))
    ax.text(5, y + 0.85, text, ha="center", va="center", fontsize=9)
    for i in range(len(steps) - 2):
        arrow(ax, 5, steps[i][0], 5, steps[i + 1][0] + 1.7)
    arrow(ax, 5, steps[4][0], 5, steps[5][0] + 2.0)
    # да / нет
    box(ax, 1.5, 1.6, 7, 1.7, "Запись нарушения: время, смена, зона, тип, фото\n(журнал SQLite)", fc="#e8e8e8")
    arrow(ax, 5, steps[5][0] - 0.3, 5, 3.3, "да", dx=0.45)
    ax.add_patch(FancyArrowPatch((9.2, steps[5][0] + 0.85), (9.7, steps[5][0] + 0.85), arrowstyle="-", lw=1.2, color=DARK))
    ax.plot([9.7, 9.7], [steps[5][0] + 0.85, 18.45], color=DARK, lw=1.2)
    ax.add_patch(FancyArrowPatch((9.7, 18.45), (8.5, 18.45), arrowstyle="-|>", mutation_scale=14, lw=1.2, color=DARK))
    ax.text(9.55, steps[5][0] + 2.3, "нет:\nследующий\nкадр", fontsize=8.5, ha="right")
    box(ax, 1.5, -0.6, 7, 1.5, "Окно мониторинга, журнал по сменам,\nакт нарушений в формате Word", fc="#e8e8e8")
    arrow(ax, 5, 1.6, 5, 0.9)
    fig.tight_layout()
    fig.savefig(OUT / "fig_algorithm.png", dpi=200)
    plt.close(fig)


def fig_regions():
    w, h = 100, 300
    fig, ax = plt.subplots(figsize=(6.4, 5.4))
    ax.set_aspect("equal")
    hr = (-0.15 * w, -0.15 * h, 1.15 * w, 0.40 * h)  # x1, y1, x2, y2 в долях рамки, y вниз
    ax.add_patch(Rectangle((0, 0), w, h, fc="none", ec=DARK, lw=2))
    ax.add_patch(Rectangle((hr[0], hr[1]), hr[2] - hr[0], hr[3] - hr[1], fc="#cfcfcf", ec=DARK, lw=1, ls="--", alpha=0.8))
    ax.add_patch(Rectangle((-0.10 * w, 0.15 * h), 1.2 * w, 0.60 * h, fc="#ededed", ec=DARK, lw=1, ls="--", alpha=0.8))
    ax.add_patch(Rectangle((20, 0), 60, 40, fc="white", ec=DARK, lw=1.6))
    ax.text(50, 20, "каска", ha="center", va="center", fontsize=9)
    ax.add_patch(Rectangle((10, 80), 80, 90, fc="white", ec=DARK, lw=1.6))
    ax.text(50, 125, "жилет", ha="center", va="center", fontsize=9)
    ax.text(w + 12, -10, "область головы:\nцентр рамки каски\nдолжен лежать здесь", fontsize=8.5, va="center")
    ax.text(w + 25, 160, "область торса:\nцентр рамки жилета здесь,\nи не менее 50% его\nплощади внутри рамки\nчеловека", fontsize=8.5, va="center")
    ax.text(50, h + 18, "рамка человека (ширина w, высота h)", ha="center", fontsize=9)
    ax.set_xlim(-60, 240)
    ax.set_ylim(h + 40, -80)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(OUT / "fig_regions.png", dpi=200)
    plt.close(fig)


def simulate(present_chance: float, seed: int, seconds: float = 10.0):
    from svision.rules import Detection, RulesParams, ViolationEngine, Zone

    zone = Zone("Зона А", ((0, 0), (1, 0), (1, 1), (0, 1)), ("helmet", "vest"))
    engine = ViolationEngine([zone], RulesParams())
    person = (400.0, 300.0, 500.0, 600.0)
    vest = Detection("vest", 0.9, (410.0, 380.0, 490.0, 470.0))
    helmet = Detection("helmet", 0.9, (420.0, 300.0, 480.0, 340.0))
    rng = random.Random(seed)
    ts, seen, confirmed_at = [], [], None
    t = 0.0
    while t <= seconds:
        found = rng.random() < present_chance
        res = engine.update(t, [(1, person)], [vest] + ([helmet] if found else []), 1000, 1000)
        ts.append(t)
        seen.append(1 if found else 0)
        if res.new and confirmed_at is None:
            confirmed_at = t
        t = round(t + 0.1, 3)
    return ts, seen, confirmed_at


def fig_window():
    fig, axes = plt.subplots(2, 1, figsize=(9, 5.2), sharex=True)
    cases = [("а) Работник в каске: модель находит каску лишь в ~75% кадров", 0.75, 0),
             ("б) Работник без каски: модель в ~17% кадров ошибочно «находит» каску", 0.17, 1)]
    for ax, (title, chance, seed) in zip(axes, cases):
        ts, seen, confirmed = simulate(chance, seed)
        ax.scatter(ts, seen, s=14, color=DARK)
        ax.set_yticks([0, 1])
        ax.set_yticklabels(["каски нет\nв кадре", "каска\nнайдена"])
        ax.set_ylim(-0.4, 1.4)
        ax.set_title(title, fontsize=10, loc="left")
        ax.grid(axis="x", color="#cccccc", lw=0.6)
        if confirmed is not None:
            ax.axvline(confirmed, color="black", lw=2)
            ax.text(confirmed + 0.1, 1.15, f"нарушение зафиксировано\nна {confirmed:.1f} с", fontsize=9, va="center")
            ax.axvspan(confirmed, ts[-1], color=GRAY, alpha=0.6)
        else:
            ax.text(5, 0.5, "нарушение не фиксируется", fontsize=9, ha="center", va="center",
                    bbox=dict(boxstyle="round", fc="white", ec=DARK))
    axes[1].set_xlabel("время, с")
    fig.tight_layout()
    fig.savefig(OUT / "fig_window.png", dpi=200)
    plt.close(fig)
    return simulate(0.75, 0)[2], simulate(0.17, 1)[2]


def fig_architecture():
    fig, ax = plt.subplots(figsize=(10, 6.4))
    ax.set_xlim(0, 20)
    ax.set_ylim(0, 13)
    ax.axis("off")
    box(ax, 0.5, 11.0, 19, 1.5, "main.py — запуск приложения, загрузка config/default.json", fc=GRAY, bold=True)
    box(ax, 0.5, 6.9, 8.6, 3.3, "Интерфейс (svision/ui)\nMainWindow\nMonitorTab — видео и таблица нарушений\nJournalTab — календарь, смены, фото\nVideoWorker — фоновый поток", fc=LIGHT)
    box(ax, 10.9, 6.9, 8.6, 3.3, "Конвейер обработки кадра (Pipeline)\nYoloDetector — нейросеть\nIoUTracker — трекинг людей\nViolationEngine — правила и зоны", fc=LIGHT)
    box(ax, 0.5, 2.4, 5.6, 3.4, "Storage (SQLite)\nжурнал нарушений,\nсмены, фото", fc="#e8e8e8")
    box(ax, 7.2, 2.4, 5.6, 3.4, "report.py\nакт нарушений\nв формате .docx", fc="#e8e8e8")
    box(ax, 13.9, 2.4, 5.6, 3.4, "Конфигурация (JSON)\nзоны, СИЗ, пороги,\nсмены, пути", fc="#e8e8e8")
    arrow(ax, 4.8, 11.0, 4.8, 10.2)
    arrow(ax, 15.2, 11.0, 15.2, 10.2)
    arrow(ax, 9.1, 8.5, 10.9, 8.5, "кадр\nи события", dy=0.9)
    arrow(ax, 3.3, 6.9, 3.3, 5.8)
    arrow(ax, 7.0, 6.9, 9.5, 5.8)
    arrow(ax, 15.2, 6.9, 16.6, 5.8)
    fig.tight_layout()
    fig.savefig(OUT / "fig_architecture.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    fig_timeline()
    fig_algorithm()
    fig_regions()
    print("моделирование: подтверждение у работника в каске =", simulate(0.75, 0)[2], "| у работника без каски =", simulate(0.17, 1)[2])
    fig_window()
    fig_architecture()
    print("готово:", sorted(p.name for p in OUT.glob("*.png")))
