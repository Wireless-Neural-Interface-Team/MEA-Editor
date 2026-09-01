"""
Qt scene wrapper exposing dynamic axis coordinates.

Axes (X/Y) are provided by an external callback, typically derived
from electrode positions for grid and tick labels.
"""

from __future__ import annotations

try:
    from PySide6.QtWidgets import QGraphicsScene
except ImportError as exc:
    raise SystemExit("PySide6 is required. Install with: pip install PySide6") from exc


class GridScene(QGraphicsScene):
    """
    Qt scene wrapper exposing dynamic axis coordinates.

    Axes (X/Y) are provided by an external callback, typically derived
    from electrode positions for grid and tick labels.
    """

    def __init__(self, parent=None) -> None:
        """Initialize scene with default axes provider (empty lists)."""
        super().__init__(parent)
        # Default: no axes (empty lists).
        self._axes_provider = lambda view=None: ([], [])
        self._pad_link_provider = lambda: ()
        # Last focused mapping view (for generic helpers).
        self.active_view = None
        # Dedicated cameras so electrode/pad labels follow their own zoom.
        self.electrode_map_view = None
        self.pad_map_view = None
        # Fast path for label contrast: skip Difference blending when unused.
        self.has_orientation_markers = False

    def view_scale(self, preferred_view=None) -> float:
        """
        Scale of a mapping view (scene units per pixel).

        Labels use ItemIgnoresTransformations. Each contact has one copy per
        camera so zooming a view only moves that view's text.
        """
        view = preferred_view if preferred_view is not None else self.active_view
        if view is None:
            views = self.views()
            if not views:
                return 1.0
            view = views[0]
        t = view.transform()
        scale = abs(t.m11()) if t.m11() != 0 else 1.0
        return max(scale, 1e-6)

    def set_axes_provider(self, provider) -> None:
        """
        Set the callback that provides axis values.

        Args:
            provider: No-arg function returning (x_list, y_list).
        """
        self._axes_provider = provider

    def get_axes(self, view=None) -> tuple[list[float], list[float]]:
        """
        Return current X/Y coordinates for grid and axes.

        Args:
            view: Mapping viewport requesting the axes, or None.

        Returns:
            (xs, ys): sorted lists of unique abscissas and ordinates.
        """
        return self._axes_provider(view)

    def set_pad_link_provider(self, provider) -> None:
        """Set the callback that provides pad-to-electrode line segments."""
        self._pad_link_provider = provider

    def pad_link_segments(self) -> tuple:
        """Return (x1, y1, x2, y2) segments drawn in the pad mapping view."""
        return self._pad_link_provider()
