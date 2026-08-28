"""
Pad frame layout around an electrode array.

Pads are placed on one or more rectangular rings surrounding the electrode
bounding box. Counts per ring follow ring perimeters so the frame stays
aligned with the electrode array aspect ratio. Electrodes and pads are then
paired by angle (and radius) so links stay locally consistent.
"""

from __future__ import annotations

import math

from .contact_shape import contact_half_extents, normalize_contact_shape
from .electrode import DEFAULT_RADIUS, Electrode
from .pad import DEFAULT_PAD_RADIUS, DEFAULT_PAD_SHAPE, Pad


def _split_counts(n: int, weights: list[float]) -> list[int]:
    """Distribute n items across rings with the largest-remainder method."""
    k = len(weights)
    if n <= 0 or k <= 0:
        return [0] * k
    if n <= k:
        return [1 if i < n else 0 for i in range(k)]
    total = sum(weights)
    if total <= 0:
        weights = [1.0] * k
        total = float(k)
    exact = [n * w / total for w in weights]
    counts = [int(x) for x in exact]
    remainder = n - sum(counts)
    order = sorted(range(k), key=lambda i: exact[i] - counts[i], reverse=True)
    for i in range(remainder):
        counts[order[i]] += 1
    return counts


def _point_on_rectangle(
    left: float,
    right: float,
    bottom: float,
    top: float,
    distance: float,
) -> tuple[float, float]:
    """Point at arc-length `distance` along the rectangle, clockwise from top-left."""
    width = max(right - left, 1e-9)
    height = max(top - bottom, 1e-9)
    peri = 2.0 * (width + height)
    d = distance % peri
    if d <= width:
        return left + d, top
    d -= width
    if d <= height:
        return right, top - d
    d -= height
    if d <= width:
        return right - d, bottom
    d -= width
    return left, bottom + d


def _pads_on_rectangle(
    left: float,
    right: float,
    bottom: float,
    top: float,
    count: int,
) -> list[tuple[float, float]]:
    """Evenly spaced pad centers on a closed rectangular ring."""
    if count <= 0:
        return []
    width = max(right - left, 1e-9)
    height = max(top - bottom, 1e-9)
    peri = 2.0 * (width + height)
    return [_point_on_rectangle(left, right, bottom, top, (i / count) * peri) for i in range(count)]


def _angular_key(x: float, y: float, cx: float, cy: float) -> tuple[float, float]:
    dx = x - cx
    dy = y - cy
    return math.atan2(dy, dx), dx * dx + dy * dy


def layout_pads_around_electrodes(
    electrodes: list[Electrode],
    *,
    pad_rows: int,
    pad_spacing: float,
    pad_size: float = DEFAULT_PAD_RADIUS,
    pad_shape: str = DEFAULT_PAD_SHAPE,
    pad_height: float = 0.0,
    electrode_radius: float = DEFAULT_RADIUS,
) -> list[Pad]:
    """
    Build one pad per electrode, arranged on `pad_rows` rectangles around the array.

    `pad_spacing` is the gap between pad rows and the target pitch along each ring.
    """
    if not electrodes:
        return []
    rows = max(int(pad_rows), 1)
    spacing = max(float(pad_spacing), 1e-6)
    size = max(float(pad_size), 1e-6)
    shape = normalize_contact_shape(pad_shape, DEFAULT_PAD_SHAPE)
    height = max(float(pad_height), 0.0)
    _half_x, half_y = contact_half_extents(shape, size, height)
    pad_extent = max(size, half_y)

    xs = [m.x for m in electrodes]
    ys = [m.y for m in electrodes]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    clearance = electrode_radius + pad_extent + spacing
    inner_left = min_x - clearance
    inner_right = max_x + clearance
    inner_bottom = min_y - clearance
    inner_top = max_y + clearance

    perimeters: list[float] = []
    frames: list[tuple[float, float, float, float]] = []
    for ring in range(rows):
        grow = ring * spacing
        left = inner_left - grow
        right = inner_right + grow
        bottom = inner_bottom - grow
        top = inner_top + grow
        frames.append((left, right, bottom, top))
        perimeters.append(2.0 * ((right - left) + (top - bottom)))

    counts = _split_counts(len(electrodes), perimeters)
    positions: list[tuple[float, float]] = []
    for frame, count in zip(frames, counts):
        positions.extend(_pads_on_rectangle(*frame, count))

    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)
    electrodes_sorted = sorted(electrodes, key=lambda m: _angular_key(m.x, m.y, cx, cy))
    pad_order = sorted(range(len(positions)), key=lambda i: _angular_key(*positions[i], cx, cy))

    pads: list[Pad] = []
    for pid, (electrode, pos_index) in enumerate(zip(electrodes_sorted, pad_order)):
        x, y = positions[pos_index]
        pads.append(
            Pad(
                pid=pid,
                electrode_eid=electrode.eid,
                x=x,
                y=y,
                radius=size,
                height=height,
                shape=shape,
            )
        )
    return pads
