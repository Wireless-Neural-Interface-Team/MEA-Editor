"""
Interactive graphics item bound to one OrientationMarker model.

Drawn as a white circle, square, or rect. Not linked to an electrode or pad,
and not labelled on the maps.
"""

from __future__ import annotations

try:
    from PySide6.QtGui import QBrush, QColor, QPainterPath
    from PySide6.QtWidgets import QGraphicsItem, QGraphicsPathItem
except ImportError as exc:
    raise SystemExit("PySide6 is required. Install with: pip install PySide6") from exc

from .contact_shape import contact_path_box
from .electrode_array_view import _option_without_qt_selection
from .orientation_marker import OrientationMarker
from .view_style import ORIENTATION_MARKER_FILL, ORIENTATION_MARKER_OUTLINE, cosmetic_pen


class OrientationMarkerView(QGraphicsPathItem):
    """
    Interactive graphics item bound to one `OrientationMarker` model.

    Drawn as circle, square, or rect according to `model.shape`. Fill is white;
    selected state uses the same yellow highlight as electrodes and pads.
    No map label is shown.
    """

    def __init__(self, model: OrientationMarker, on_change, on_selection_change) -> None:
        super().__init__()
        self.model = model
        self._on_change = on_change
        self._on_selection_change = on_selection_change
        self.setFlags(
            QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setZValue(8)
        self.setAcceptHoverEvents(False)
        self.set_radius(model.radius)
        self.setPos(model.x, model.y)
        self._refresh_style()

    def set_radius(self, radius: float) -> None:
        """Update model radius and rebuild the marker path."""
        self.model.radius = radius
        self._update_path()

    def set_height(self, height: float) -> None:
        """Update model height and rebuild the marker path."""
        self.model.height = height
        self._update_path()

    def _update_path(self) -> None:
        """Rebuild path geometry from the marker shape, radius, and height."""
        kind, x, y, w, h = contact_path_box(self.model.shape, self.model.radius, self.model.height)
        path = QPainterPath()
        if kind == "ellipse":
            path.addEllipse(x, y, w, h)
        else:
            path.addRect(x, y, w, h)
        self.setPath(path)

    def _refresh_style(self) -> None:
        """White fill; yellow when selected."""
        if self.isSelected():
            fill = QColor("#ffd447")
            outline = QColor("#f6f7f8")
        else:
            fill = QColor(ORIENTATION_MARKER_FILL)
            outline = QColor(ORIENTATION_MARKER_OUTLINE)
        self.setBrush(QBrush(fill))
        self.setPen(cosmetic_pen(outline, 2))

    def paint(self, painter, option, widget=None) -> None:  # type: ignore[override]
        super().paint(painter, _option_without_qt_selection(option), widget)

    def itemChange(self, change, value):  # type: ignore[override]
        """Copy x/y to model on position change; refresh style and panel on selection."""
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
        """Apply model state to visual item."""
        self.setPos(self.model.x, self.model.y)
        self.set_radius(self.model.radius)
        self._refresh_style()
