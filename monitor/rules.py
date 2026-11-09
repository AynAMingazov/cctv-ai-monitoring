"""Business rules on top of person detections.

Each rule receives, for every frame, a list of tracked people:
    Person(track_id, box, wrists)  — wrists are (x, y) keypoints from a pose model
and returns a list of events (dicts) to be logged and, if needed, sent as alerts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time as dtime

from .geometry import Point, foot_point, point_in_polygon, side_of_line


@dataclass
class Person:
    track_id: int
    box: tuple[float, float, float, float]
    wrists: list[Point] = field(default_factory=list)


def _in_hours(now: datetime, start: dtime, end: dtime) -> bool:
    t = now.time()
    return start <= t < end if start < end else (t >= start or t < end)


class NightDoorRule:
    """Alert when someone is near a door during closed hours."""

    def __init__(self, name: str, zone: list[Point], start: str = "21:00", end: str = "08:00",
                 cooldown_s: int = 300):
        self.name, self.zone, self.cooldown = name, zone, cooldown_s
        self.start, self.end = dtime.fromisoformat(start), dtime.fromisoformat(end)
        self._last_alert: datetime | None = None

    def update(self, people: list[Person], now: datetime) -> list[dict]:
        if not _in_hours(now, self.start, self.end):
            return []
        intruders = [p.track_id for p in people if point_in_polygon(foot_point(p.box), self.zone)]
        if not intruders:
            return []
        if self._last_alert and (now - self._last_alert).total_seconds() < self.cooldown:
            return []
        self._last_alert = now
        return [{"type": "night_door", "zone": self.name, "tracks": intruders, "alert": True}]


class LineCounter:
    """Counts people crossing an entrance line (in / out) by track id."""

    def __init__(self, name: str, a: Point, b: Point, inside_sign: int = 1):
        self.name, self.a, self.b, self.inside_sign = name, a, b, inside_sign
        self._side: dict[int, int] = {}
        self.count_in = 0
        self.count_out = 0

    def update(self, people: list[Person], now: datetime) -> list[dict]:
        events = []
        for p in people:
            side = side_of_line(foot_point(p.box), self.a, self.b)
            if side == 0:
                continue
            prev = self._side.get(p.track_id)
            self._side[p.track_id] = side
            if prev is None or prev == side:
                continue
            direction = "in" if side == self.inside_sign else "out"
            if direction == "in":
                self.count_in += 1
            else:
                self.count_out += 1
            events.append({"type": "visitor_" + direction, "zone": self.name, "tracks": [p.track_id]})
        return events


class ZoneVisitRule:
    """Logs each visit of a person to a zone with its duration (e.g. the oil dispensing point)."""

    def __init__(self, name: str, zone: list[Point], min_seconds: float = 3, use_wrists: bool = False):
        self.name, self.zone, self.min_seconds, self.use_wrists = name, zone, min_seconds, use_wrists
        self._enter: dict[int, datetime] = {}

    def _inside(self, p: Person) -> bool:
        if self.use_wrists:
            return any(point_in_polygon(w, self.zone) for w in p.wrists)
        return point_in_polygon(foot_point(p.box), self.zone)

    def update(self, people: list[Person], now: datetime) -> list[dict]:
        events = []
        present = {p.track_id for p in people if self._inside(p)}
        for tid in present - self._enter.keys():
            self._enter[tid] = now
        for tid in list(self._enter.keys() - present):
            started = self._enter.pop(tid)
            seconds = (now - started).total_seconds()
            if seconds >= self.min_seconds:
                kind = "hands_in_zone" if self.use_wrists else "zone_visit"
                events.append({"type": kind, "zone": self.name, "tracks": [tid],
                               "started": started.isoformat(timespec="seconds"), "seconds": round(seconds, 1)})
        return events
