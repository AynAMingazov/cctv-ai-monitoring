from datetime import datetime, timedelta

from monitor.geometry import point_in_polygon, side_of_line
from monitor.rules import LineCounter, NightDoorRule, Person, ZoneVisitRule
from reconcile import reconcile

SQUARE = [(0, 0), (100, 0), (100, 100), (0, 100)]


def person(tid, x, y, wrists=()):
    # box whose bottom-centre (foot point) is (x, y)
    return Person(tid, (x - 10, y - 50, x + 10, y), list(wrists))


def test_point_in_polygon():
    assert point_in_polygon((50, 50), SQUARE)
    assert not point_in_polygon((150, 50), SQUARE)


def test_side_of_line():
    assert side_of_line((0, 1), (0, 0), (1, 0)) == 1
    assert side_of_line((0, -1), (0, 0), (1, 0)) == -1


def test_night_door_alerts_only_at_night_with_cooldown():
    rule = NightDoorRule("door", SQUARE, "21:00", "08:00", cooldown_s=300)
    day, night = datetime(2026, 10, 1, 14, 0), datetime(2026, 10, 1, 23, 0)
    assert rule.update([person(1, 50, 50)], day) == []
    assert rule.update([person(1, 50, 50)], night)[0]["type"] == "night_door"
    assert rule.update([person(1, 50, 50)], night + timedelta(seconds=60)) == []      # cooldown
    assert rule.update([person(1, 50, 50)], night + timedelta(seconds=400)) != []
    assert rule.update([person(2, 500, 500)], night + timedelta(seconds=900)) == []   # outside zone


def test_line_counter_counts_crossings_once():
    counter = LineCounter("entrance", (0, 100), (200, 100), inside_sign=1)
    t = datetime(2026, 10, 1, 12, 0)
    counter.update([person(7, 50, 90)], t)          # outside
    counter.update([person(7, 50, 95)], t)          # still outside
    events = counter.update([person(7, 50, 110)], t)  # crossed
    counter.update([person(7, 50, 120)], t)         # stays inside
    assert [e["type"] for e in events] == ["visitor_in"]
    assert counter.count_in == 1 and counter.count_out == 0


def test_zone_visit_logs_duration():
    rule = ZoneVisitRule("oil", SQUARE, min_seconds=3)
    t0 = datetime(2026, 10, 1, 12, 0)
    rule.update([person(3, 50, 50)], t0)
    rule.update([person(3, 50, 50)], t0 + timedelta(seconds=5))
    events = rule.update([], t0 + timedelta(seconds=8))
    assert events[0]["type"] == "zone_visit" and events[0]["seconds"] == 8.0


def test_short_visit_is_ignored():
    rule = ZoneVisitRule("oil", SQUARE, min_seconds=3)
    t0 = datetime(2026, 10, 1, 12, 0)
    rule.update([person(3, 50, 50)], t0)
    assert rule.update([], t0 + timedelta(seconds=1)) == []


def test_hands_zone_uses_wrists_not_feet():
    rule = ZoneVisitRule("cash", SQUARE, min_seconds=1, use_wrists=True)
    t0 = datetime(2026, 10, 1, 12, 0)
    rule.update([person(4, 500, 500, wrists=[(50, 50)])], t0)
    events = rule.update([person(4, 500, 500, wrists=[])], t0 + timedelta(seconds=2))
    assert events[0]["type"] == "hands_in_zone"


def test_reconcile_flags_unregistered_visits():
    assert reconcile(5, 3)["check_needed"] and reconcile(5, 3)["unregistered"] == 2
    assert not reconcile(20, 19)["check_needed"]
