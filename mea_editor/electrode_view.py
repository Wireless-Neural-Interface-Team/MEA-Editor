"""
Interactive graphics item bound to one Electrode model.

It owns:
- contact shape path (circle, square, or rect),
- center / below labels from the visible electrode IDs,
- fill color that varies by shank (blues).

Labels exist twice, once per mapping camera, so each view can position
text from its own zoom.
"""

from __future__ import annotations

from typing import Callable

try:
    from PySide6.QtGui import QColor, QPainterPath, QTransform
    from PySide6.QtWidgets import QGraphicsItem, QGraphicsPathItem
except ImportError as exc:
    raise SystemExit("PySide6 is required. Install with: pip install PySide6") from exc

from .contact_shape import contact_path_box
from .electrode import DEFAULT_PLANE_AXIS, Electrode
from .electrode_array_view import PerViewContactLabels
from .view_style import apply_contact_colors, electrode_fill_for_shank

MapLabelFn = Callable[[Electrode], tuple[str, str]]


class ElectrodeView(PerViewContactLabels, QGraphicsPathItem):
    """
    Interactive graphics item bound to one `Electrode` model.

    It owns:
    - contact shape path (circle, square, or rect),
    - center / below labels from the visible electrode IDs.
    """

    def __init__(
        self,
        model: Electrode,
        on_change,
        on_selection_change,
        map_labels: MapLabelFn | None = None,
    ) -> None:
        super().__init__()
        self.model = model
        self._on_change = on_change
        self._on_selection_change = on_selection_change
        self._map_labels = map_labels
        # ItemSendsGeometryChanges required for ItemPositionHasChanged in itemChange.
        self.setFlags(
            QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setZValue(10)  # Above grid lines.

        # Labels must exist before set_radius() (which calls _layout_labels).
        self._init_view_labels()
        self._refresh_label()
        self.set_radius(model.radius)
        self.setPos(model.x, model.y)
        self._layout_labels()
        self._refresh_style()

    def _refresh_label(self) -> None:
        """Sync label text from the visible electrode IDs and reposition labels."""
        if self._map_labels is not None:
            center, below = self._map_labels(self.model)
        else:
            center, below = self.model.map_view_labels()
        self._set_label_text(center, below)
        self._layout_labels()

    def _color_for_shank(self) -> QColor:
        """Return a blue fill color that varies by shank_id."""
        return electrode_fill_for_shank(self.model.shank_id)

    def set_radius(self, radius: float) -> None:
        """Update model radius and rebuild the contact path."""
        self.model.radius = radius
        self._update_path()

    def set_height(self, height: float) -> None:
        """Update model height and rebuild the contact path."""
        self.model.height = height
        self._update_path()

    def _update_path(self) -> None:
        """Rebuild path geometry from shape, radius, height, and plane axes."""
        kind, x, y, w, h = contact_path_box(self.model.shape, self.model.radius, self.model.height)
        path = QPainterPath()
        if kind == "ellipse":
            path.addEllipse(x, y, w, h)
        else:
            path.addRect(x, y, w, h)
        plane = self.model.contact_plane_axis
        if self.model.shape != "circle" and plane != DEFAULT_PLANE_AXIS:
            x0, x1, y0, y1 = plane
            path = QTransform(x0, x1, y0, y1, 0.0, 0.0).map(path)
        self.setPath(path)
        if hasattr(self, "_view_labels"):
            self._layout_labels()

    def _refresh_style(self) -> None:
        """
        Apply fill and outline colors based on state.

        Priority: duplicate (red) > selected (yellow) > color by shank.
        """
        is_duplicate = self.model.has_any_duplicate()
        if is_duplicate:
            apply_contact_colors(self, QColor("#d44b4b"), QColor("#ffe0e0"))
        elif self.isSelected():
            apply_contact_colors(self, QColor("#ffd447"), QColor("#f6f7f8"))
        else:
            apply_contact_colors(self, self._color_for_shank())

    def itemChange(self, change, value):  # type: ignore[override]
        """
        Qt callback fired on item state/geometry changes.

        - ItemPositionHasChanged: copy x/y to model, notify controller.
        - ItemSelectedHasChanged: refresh style and side panel.
        """
        if change == QGraphicsItem.ItemPositionHasChanged:
            p = self.pos()
            self.model.x = p.x()
            self.model.y = p.y()
            self._on_change()
        elif change == QGraphicsItem.ItemSelectedHasChanged:
            self._refresh_style()
            self._on_selection_change()
        return super().itemChange(change, value)

    def sync_from_model(self) -> None:
        """
        Apply model state to visual item.

        Updates: position, geometry, label text, colors.
        """
        self.setPos(self.model.x, self.model.y)
        self.set_radius(self.model.radius)
        self._refresh_label()
        self._refresh_style()
