from svision.pipeline import Pipeline
from svision.rules import Detection, RulesParams, ViolationEngine, Zone, ppe_present
from svision.tracking import IoUTracker, TrackerParams

W, H = 1000, 1000
FULL = Zone("Зона А", ((0, 0), (1, 0), (1, 1), (0, 1)), ("helmet", "vest"))
PERSON = (400.0, 300.0, 500.0, 600.0)  # 100x300 px
HELMET = Detection("helmet", 0.9, (420.0, 300.0, 480.0, 340.0))
VEST = Detection("vest", 0.9, (410.0, 380.0, 490.0, 470.0))


def run(engine, dets, times, person=PERSON):
    events = []
    for t in times:
        events.append(engine.update(t, [(1, person)], dets, W, H))
    return events


def frames(start, stop, step=0.25):
    t = start
    while t <= stop + 1e-9:
        yield round(t, 3)
        t += step


def test_ppe_present_helmet_and_vest():
    assert ppe_present("helmet", PERSON, [HELMET])
    assert ppe_present("vest", PERSON, [VEST])
    assert not ppe_present("helmet", PERSON, [VEST])
    assert not ppe_present("vest", PERSON, [HELMET])


def test_helmet_far_from_head_does_not_count():
    lying_helmet = Detection("helmet", 0.9, (420.0, 560.0, 480.0, 600.0))
    assert not ppe_present("helmet", PERSON, [lying_helmet])


def test_negative_class_wins_when_more_confident():
    no_helmet = Detection("no_helmet", 0.95, (420.0, 300.0, 480.0, 340.0))
    weak_helmet = Detection("helmet", 0.5, HELMET.box)
    assert not ppe_present("helmet", PERSON, [weak_helmet, no_helmet])
    assert ppe_present("helmet", PERSON, [weak_helmet, no_helmet], use_negative=False)


def test_compliant_person_never_violates():
    engine = ViolationEngine([FULL])
    results = run(engine, [HELMET, VEST], frames(0, 10))
    assert all(not r.new and not r.active for r in results)
    assert results[-1].persons[0].state == "ok"


def test_missing_helmet_confirmed_after_threshold_once():
    engine = ViolationEngine([FULL], RulesParams(confirm_seconds=3.0))
    results = run(engine, [VEST], frames(0, 8))
    new = [e for r in results for e in r.new]
    assert len(new) == 1
    assert new[0].kind == "no_helmet"
    assert 3.0 <= new[0].t <= 3.25
    assert results[1].persons[0].state == "warning"
    assert results[-1].persons[0].state == "violation"
    assert [a.kind for a in results[-1].active] == ["no_helmet"]


def test_both_violations_reported():
    engine = ViolationEngine([FULL])
    results = run(engine, [], frames(0, 5))
    kinds = sorted(e.kind for r in results for e in r.new)
    assert kinds == ["no_helmet", "no_vest"]


def test_short_gap_below_threshold_is_not_a_violation():
    engine = ViolationEngine([FULL], RulesParams(confirm_seconds=3.0))
    results = run(engine, [VEST], frames(0, 2.5)) + run(engine, [HELMET, VEST], frames(2.75, 6))
    assert not any(r.new for r in results)
    assert results[-1].persons[0].state == "ok"


def test_flicker_does_not_reset_timer():
    """Каска «мигает» на 1 кадр: нарушение всё равно фиксируется."""
    engine = ViolationEngine([FULL], RulesParams(confirm_seconds=3.0, clear_seconds=2.0))
    results = run(engine, [VEST], frames(0, 1.5))
    results += run(engine, [HELMET, VEST], [1.75])
    results += run(engine, [VEST], frames(2.0, 5))
    assert sum(len(r.new) for r in results) == 1


def test_resolution_reports_duration_and_allows_new_episode():
    engine = ViolationEngine([FULL], RulesParams(confirm_seconds=3.0, clear_seconds=2.0, dedup_seconds=0.0))
    results = run(engine, [VEST], frames(0, 5))
    results += run(engine, [HELMET, VEST], frames(5.25, 8))
    resolved = [e for r in results for e in r.resolved]
    assert len(resolved) == 1
    assert 4.5 <= resolved[0].duration_s <= 5.0
    assert not results[-1].active
    results = run(engine, [VEST], frames(8.25, 13))
    assert sum(len(r.new) for r in results) == 1


def test_person_outside_zone_or_too_small_is_ignored():
    left_half = Zone("Левая", ((0, 0), (0.3, 0), (0.3, 1), (0, 1)), ("helmet",))
    engine = ViolationEngine([left_half])
    results = run(engine, [], frames(0, 6))  # человек в центре кадра, вне зоны
    assert not any(r.new for r in results)
    assert results[-1].persons[0].state == "ignored"

    engine = ViolationEngine([FULL])
    tiny = (400.0, 500.0, 410.0, 540.0)  # 40 px = 4% высоты кадра
    results = run(engine, [], frames(0, 6), person=tiny)
    assert not any(r.new for r in results)


def test_zone_specific_requirements():
    helmet_only = Zone("Только каска", ((0, 0), (1, 0), (1, 1), (0, 1)), ("helmet",))
    engine = ViolationEngine([helmet_only])
    results = run(engine, [HELMET], frames(0, 6))  # жилета нет, но он тут не обязателен
    assert not any(r.new for r in results)


def test_dedup_when_track_id_changes_for_same_place():
    engine = ViolationEngine([FULL], RulesParams(confirm_seconds=1.0, clear_seconds=1.0, dedup_seconds=15.0))
    first = [engine.update(t, [(1, PERSON)], [VEST], W, H) for t in frames(0, 2)]
    assert sum(len(r.new) for r in first) == 1
    gap = [engine.update(t, [], [], W, H) for t in frames(2.25, 3.5)]  # трек пропал
    assert any(r.resolved for r in gap)
    second = [engine.update(t, [(2, PERSON)], [VEST], W, H) for t in frames(3.75, 6)]
    assert sum(len(r.new) for r in second) == 0  # тот же человек под новым номером


def test_two_people_side_by_side_are_both_reported():
    engine = ViolationEngine([FULL], RulesParams(confirm_seconds=1.0))
    other = (520.0, 300.0, 620.0, 600.0)
    new = []
    for t in frames(0, 3):
        new += engine.update(t, [(1, PERSON), (2, other)], [], W, H).new
    assert sorted((e.track_id, e.kind) for e in new) == [(1, "no_helmet"), (1, "no_vest"), (2, "no_helmet"), (2, "no_vest")]


class ScriptedDetector:
    """Для тестов: заранее заданные детекции по номеру кадра."""
    def __init__(self, script):
        self.script, self.i = script, 0

    def detect(self, frame):
        dets = self.script[min(self.i, len(self.script) - 1)]
        self.i += 1
        return dets


def test_pipeline_tracks_person_and_flags_violation():
    import numpy as np

    person = Detection("person", 0.9, PERSON)
    script = [[person, VEST]] * 20
    pipeline = Pipeline(ScriptedDetector(script), IoUTracker(TrackerParams()),
                        ViolationEngine([FULL], RulesParams(confirm_seconds=2.0)))
    frame = np.zeros((H, W, 3), dtype=np.uint8)
    new = []
    for i in range(20):
        new += pipeline.process(frame, i * 0.25).result.new
    assert [e.kind for e in new] == ["no_helmet"]
