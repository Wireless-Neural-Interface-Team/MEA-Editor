"""
Contact shapes shared by electrodes and pads.

SpikeInterface / probeinterface supports exactly three contact geometries:
- circle: shape_params = {"radius": float}
- square: shape_params = {"width": float}
- rect:   shape_params = {"width": float, "height": float}

Internally, `radius` is the stored half-extent along X (true radius for a
circle, half-width for square/rect). `height` is the stored half-extent along
Y for `rect` only; 0 means "same as radius".
"""

from __future__ import annotations

from typing import Any

CONTACT_SHAPES = ("circle", "square", "rect")
DEFAULT_ELECTRODE_SHAPE = "circle"
DEFAULT_PAD_SHAPE = "square"


def normalize_contact_shape(shape: str, default: str) -> str:
    """Return a supported shape, or `default` when the value is unknown."""
    text = str(shape).strip().lower() or default
    if text in CONTACT_SHAPES:
        return text
    return default if default in CONTACT_SHAPES else DEFAULT_ELECTRODE_SHAPE


def shape_uses_height(shape: str) -> bool:
    """True when the geometry needs an independent Y size (rect)."""
    return str(shape).strip().lower() == "rect"


def primary_size_field_label(shape: str) -> str:
    """UI label for the main size field."""
    kind = str(shape).strip().lower()
    if kind == "square":
        return "Side length"
    if kind == "rect":
        return "Width"
    return "Radius"


def height_field_label() -> str:
    """UI label for the rect height field (full extent)."""
    return "Height"


def stored_half_from_size_field(shape: str, size_value: float) -> float:
    """Convert the UI size (radius or full width/height) into stored half-extent."""
    if str(shape).strip().lower() == "circle":
        return size_value
    return size_value / 2.0


def size_field_from_stored_half(shape: str, half: float) -> float:
    """Convert stored half-extent into the value shown in the size field."""
    if str(shape).strip().lower() == "circle":
        return half
    return half * 2.0


def effective_half_height(shape: str, radius: float, height: float) -> float:
    """Half-extent along Y used for drawing and bounds."""
    if str(shape).strip().lower() != "rect":
        return radius
    return height if height > 0 else radius


def export_contact_sizes(
    shape: str, radius: float, height: float
) -> tuple[float | None, float | None, float | None]:
    """
    Size columns for Excel: (radius, width, height).

    Only the parameters used by `shape` are filled; the others are None
    (empty cells). Width and height are full extents. A square fills both
    width and height with the same side length.
    """
    kind = str(shape).strip().lower()
    if kind == "square":
        side = size_field_from_stored_half("square", radius)
        return None, side, side
    if kind == "rect":
        half_h = effective_half_height(kind, radius, height)
        return (
            None,
            size_field_from_stored_half("rect", radius),
            size_field_from_stored_half("rect", half_h),
        )
    return size_field_from_stored_half("circle", radius), None, None


def contact_half_extents(shape: str, radius: float, height: float) -> tuple[float, float]:
    """Return (half_width, half_height) for the given geometry."""
    return radius, effective_half_height(shape, radius, height)


def contact_path_box(shape: str, radius: float, height: float) -> tuple[str, float, float, float, float]:
    """
    Geometry for a QPainterPath centered at the origin.

    Returns:
        (kind, x, y, w, h) with kind in {"ellipse", "rect"}.
    """
    kind = str(shape).strip().lower()
    if kind == "circle":
        return "ellipse", -radius, -radius, 2.0 * radius, 2.0 * radius
    half_h = effective_half_height(kind, radius, height)
    return "rect", -radius, -half_h, 2.0 * radius, 2.0 * half_h


def probe_shape_params(shape: str, radius: float, height: float, min_radius: float) -> dict[str, float]:
    """probeinterface `contact_shape_params` entry for one contact."""
    half_w = max(float(radius), min_radius)
    kind = normalize_contact_shape(shape, DEFAULT_ELECTRODE_SHAPE)
    if kind == "square":
        return {"width": half_w * 2.0}
    if kind == "rect":
        half_h = max(float(height) if height > 0 else half_w, min_radius)
        return {"width": half_w * 2.0, "height": half_h * 2.0}
    return {"radius": half_w}


def extents_from_probe_params(
    shape: str,
    params: Any,
    default_radius: float,
    min_radius: float,
) -> tuple[float, float]:
    """
    Parse probeinterface shape_params into stored (radius, height).

    `height` is 0 for circle/square (unused).
    """
    if not isinstance(params, dict):
        params = {}
    kind = normalize_contact_shape(shape, DEFAULT_ELECTRODE_SHAPE)
    if kind == "circle":
        radius = params.get("radius", default_radius)
        return max(_as_positive_float(radius, default_radius), min_radius), 0.0
    width = params.get("width")
    if kind == "square":
        side = _as_positive_float(width, default_radius * 2.0)
        return max(side / 2.0, min_radius), 0.0
    height = params.get("height")
    full_w = _as_positive_float(width, default_radius * 2.0)
    full_h = _as_positive_float(height, full_w)
    return max(full_w / 2.0, min_radius), max(full_h / 2.0, min_radius)


def _as_positive_float(value: Any, default: float) -> float:
    try:
        if value is None:
            return default
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number != number or number <= 0:
        return default
    return number
