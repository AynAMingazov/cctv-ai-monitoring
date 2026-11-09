"""Small geometry helpers (pure Python, easy to test)."""
from __future__ import annotations

Point = tuple[float, float]


def point_in_polygon(p: Point, polygon: list[Point]) -> bool:
    """Ray casting test."""
    x, y = p
    inside = False
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            x_cross = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < x_cross:
                inside = not inside
    return inside


def side_of_line(p: Point, a: Point, b: Point) -> int:
    """+1 / -1 depending on which side of line AB the point is, 0 if on the line."""
    cross = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
    return (cross > 0) - (cross < 0)


def foot_point(box: tuple[float, float, float, float]) -> Point:
    """Bottom-centre of a bounding box: where the person stands."""
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2, y2)
