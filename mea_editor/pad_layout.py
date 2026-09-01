"""
Pad frame layout around an electrode array.

Pads are placed on one or more rectangular rings surrounding the electrode
bounding box. `pad_spacing` is the center-to-center pitch between adjacent
pads, along each ring and between rings, matching electrode pitch. Counts per
ring follow ring perimeters so the frame stays aligned with the electrode
array aspect ratio. Electrodes and pads are then paired by angle (and radius)
so links stay locally consistent.
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


def _axis_steps(sum_steps: int, span_x: float, span_y: float) -> tuple[int, int]:
    """Split `sum_steps` into (nx, ny) following the electrode aspect ratio."""
    if sum_steps <= 1:
        return max(sum_steps, 1), 0
    nx = int(round(sum_steps * span_x / (span_x + span_y)))
    nx = min(max(nx, 1), sum_steps - 1)
    ny = sum_steps - nx
    if ny < 1:
        ny = 1
        nx = sum_steps - 1
    return nx, ny


def _target_inner_perimeter(n: int, rows: int, spacing: float, min_peri: float) -> float:
    """
    Inner-ring perimeter so each ring can hold pads at pitch `spacing`.

    Outer ring r is 8 spacing-steps larger than ring 0 (width and height each
    grow by 2 steps). Choose the inner perimeter so the sum of pads per ring
    matches `n` when every along-ring step equals `spacing`.
    """
    rows = max(int(rows), 1)
    if rows == 1:
        return max(n * spacing, min_peri)
    inner_steps = n / rows - 4.0 * (rows - 1)
    return max(inner_steps * spacing, min_peri)


def _rectangle_wh(
    peri: float,
    spacing: float,
    span_x: float,
    span_y: float,
    min_w: float,
    min_h: float,
) -> tuple[float, float]:
    """Width and height for a pad ring of perimeter `peri`."""
    total = span_x + span_y
    half = max(float(peri), 1e-9) * 0.5
    width = half * span_x / total
    height = half * span_y / total
    steps = int(round(peri / spacing))
    if steps >= 2 and steps % 2 == 0:
        nx, ny = _axis_steps(steps // 2, span_x, span_y)
        width = nx * spacing
        height = ny * spacing
    return max(width, min_w), max(height, min_h)


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

    `pad_spacing` is the center-to-center pitch between adjacent pads, along
    each ring and between concentric rings. The frame grows to honor that
    pitch when the electrode array leaves enough room; otherwise the inner
    ring is enlarged just enough that pad bodies stay outside electrode bodies.
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

    electrode_bodies: list[tuple[float, float, float, float]] = []
    for model in electrodes:
        hx, hy = contact_half_extents(model.shape, model.radius, model.height)
        hx = max(hx, float(electrode_radius))
        hy = max(hy, float(electrode_radius))
        electrode_bodies.append((model.x, model.y, hx, hy))
    min_x = min(x - hx for x, y, hx, hy in electrode_bodies)
    max_x = max(x + hx for x, y, hx, hy in electrode_bodies)
    min_y = min(y - hy for x, y, hx, hy in electrode_bodies)
    max_y = max(y + hy for x, y, hx, hy in electrode_bodies)

    span_x = max(max_x - min_x, 1e-9)
    span_y = max(max_y - min_y, 1e-9)
    min_w = span_x + 2.0 * pad_extent
    min_h = span_y + 2.0 * pad_extent
    min_peri = 2.0 * (min_w + min_h)
    cx_box = 0.5 * (min_x + max_x)
    cy_box = 0.5 * (min_y + max_y)

    peri0 = _target_inner_perimeter(len(electrodes), rows, spacing, min_peri)
    width0, height0 = _rectangle_wh(peri0, spacing, span_x, span_y, min_w, min_h)

    perimeters: list[float] = []
    frames: list[tuple[float, float, float, float]] = []
    for ring in range(rows):
        width = width0 + 2.0 * ring * spacing
        height = height0 + 2.0 * ring * spacing
        left = cx_box - 0.5 * width
        right = cx_box + 0.5 * width
        bottom = cy_box - 0.5 * height
        top = cy_box + 0.5 * height
        frames.append((left, right, bottom, top))
        perimeters.append(2.0 * (width + height))

    counts = _split_counts(len(electrodes), perimeters)
    positions: list[tuple[float, float]] = []
    for frame, count in zip(frames, counts):
        positions.extend(_pads_on_rectangle(*frame, count))

    cx = sum(model.x for model in electrodes) / len(electrodes)
    cy = sum(model.y for model in electrodes) / len(electrodes)
    electrodes_sorted = sorted(electrodes, key=lambda m: _angular_key(m.x, m.y, cx, cy))
    pad_order = sorted(range(len(positions)), key=lambda i: _angular_key(*positions[i], cx, cy))

    pads: list[Pad] = []
    for pad_id, (electrode, pos_index) in enumerate(zip(electrodes_sorted, pad_order)):
        x, y = positions[pos_index]
        pads.append(
            Pad(
                pad_id=pad_id,
                electrode_eid=electrode.eid,
                x=x,
                y=y,
                radius=size,
                height=height,
                shape=shape,
            )
        )
    return pads
