"""
Shared map-view colors for electrodes, pads, and orientation markers.

Fill colors vary by `shank_id` so contacts on the same shank stay visually
grouped: blues for electrodes, purples for pads. Consecutive shanks use
high-contrast hues and brightness so they stay easy to tell apart on the
dark canvas. Duplicate/selection/disabled states keep their own colors
in the view items.
"""

from __future__ import annotations

import hashlib

try:
    from PySide6.QtGui import QBrush, QColor, QPen
except ImportError as exc:
    raise SystemExit("PySide6 is required. Install with: pip install PySide6") from exc


def cosmetic_pen(color: QColor, width: float = 2.0) -> QPen:
    """Outline that stays a fixed pixel width at every zoom."""
    pen = QPen(color, width)
    pen.setCosmetic(True)
    return pen


ELECTRODE_DEFAULT_FILL = QColor("#3da5ff")
PAD_DEFAULT_FILL = QColor("#c77dff")
ORIENTATION_MARKER_FILL = QColor("#ffffff")
ORIENTATION_MARKER_OUTLINE = QColor("#8a9bb0")

LABEL_ON_DARK = QColor("#ffffff")
LABEL_ON_LIGHT = QColor("#0c1420")

# Bright, widely spaced blues (hue + lightness jumps between neighbors).
ELECTRODE_SHANK_BLUES: tuple[QColor, ...] = (
    QColor("#00E5FF"),  # neon cyan
    QColor("#2F6BFF"),  # royal
    QColor("#B3E5FC"),  # ice
    QColor("#0066CC"),  # cobalt
    QColor("#4DFFEA"),  # aqua
    QColor("#7C8CFF"),  # periwinkle
    QColor("#40C4FF"),  # sky
    QColor("#0097A7"),  # teal-cyan
)

# Bright, widely spaced purples (hue + lightness jumps between neighbors).
PAD_SHANK_PURPLES: tuple[QColor, ...] = (
    QColor("#FF4DFF"),  # hot magenta
    QColor("#7A3DFF"),  # deep violet
    QColor("#E8C4FF"),  # pale lavender
    QColor("#C400D4"),  # grape
    QColor("#FF9AE3"),  # pink-purple
    QColor("#9D4EDD"),  # orchid
    QColor("#B388FF"),  # light violet
    QColor("#6A00F5"),  # electric violet
)


def _channel_to_linear(value: int) -> float:
    channel = value / 255.0
    if channel <= 0.04045:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def relative_luminance(color: QColor) -> float:
    """WCAG relative luminance of a fill color (0 = black, 1 = white)."""
    return (
        0.2126 * _channel_to_linear(color.red())
        + 0.7152 * _channel_to_linear(color.green())
        + 0.0722 * _channel_to_linear(color.blue())
    )


def label_color_for_fill(fill: QColor) -> QColor:
    """Center-label color that stays readable on the contact fill."""
    if relative_luminance(fill) > 0.28:
        return QColor(LABEL_ON_LIGHT)
    return QColor(LABEL_ON_DARK)


def outline_for_fill(fill: QColor) -> QColor:
    """Lighter rim so the contact stays visible on the dark canvas."""
    return QColor(
        min(255, int(fill.red() * 0.4 + 255 * 0.6)),
        min(255, int(fill.green() * 0.4 + 255 * 0.6)),
        min(255, int(fill.blue() * 0.4 + 255 * 0.6)),
    )


def apply_contact_colors(item, fill: QColor, outline: QColor | None = None) -> None:
    """Set fill, outline, and overlay-label colors on an electrode or pad view item."""
    rim = QColor(outline) if outline is not None else outline_for_fill(fill)
    item.setBrush(QBrush(fill))
    item.setPen(cosmetic_pen(rim, 2))
    item._label_center_color = label_color_for_fill(fill)
    item._label_below_color = QColor(LABEL_ON_DARK)


def color_for_shank(
    shank_id: str,
    palette: tuple[QColor, ...],
    default: QColor,
) -> QColor:
    """
    Return a deterministic fill color for a shank id.

    Numeric shanks (0, 1, 2, ...) map to consecutive palette entries so nearby
    shanks stay easy to tell apart. Other values hash into the same palette.
    """
    shank = str(shank_id).strip()
    if not shank:
        return QColor(default)
    try:
        index = int(shank)
        if index >= 0:
            return QColor(palette[index % len(palette)])
    except ValueError:
        pass
    digest = hashlib.sha1(shank.encode("utf-8")).digest()
    return QColor(palette[digest[0] % len(palette)])


def electrode_fill_for_shank(shank_id: str) -> QColor:
    """Blue fill for an electrode, varying by shank id."""
    return color_for_shank(shank_id, ELECTRODE_SHANK_BLUES, ELECTRODE_DEFAULT_FILL)


def pad_fill_for_shank(shank_id: str) -> QColor:
    """Purple fill for a pad, varying by the linked electrode's shank id."""
    return color_for_shank(shank_id, PAD_SHANK_PURPLES, PAD_DEFAULT_FILL)
