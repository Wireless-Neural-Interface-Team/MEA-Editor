"""
Interactive graphics item bound to one OrientationMarker model.

Drawn as a white square. Not linked to an electrode or pad. The marker ID is
drawn beside the square (above / below / left / right).
"""

from __future__ import annotations

try:
    from PySide6.QtGui import QBrush, QColor, QPainterPath, QPen
    from PySide6.QtWidgets import QGraphicsItem, QGraphicsPathItem
except ImportError as exc:
    raise SystemExit("PySide6 is required. Install with: pip install PySide6") from exc

from .contact_shape import contact_path_box
from .electrode_array_view import PerViewContactLabels
from .orientation_marker import OrientationMarker
from .view_style import LABEL_ON_DARK, ORIENTATION_MARKER_FILL, ORIENTATION_MARKER_OUTLINE


class OrientationMarkerView(PerViewContactLabels, QGraphicsPathItem):
    """
    Interactive graphics item bound to one `OrientationMarker` model.

    Always a square. Fill is white; selected state uses the same yellow
    highlight as electrodes and pads. The marker ID is drawn outside the
    square according to `model.label_position`.
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
        self._init_view_labels()
        self._refresh_label()
        self.set_side(model.side)
        self.setPos(model.x, model.y)
        self._layout_labels()
        self._refresh_style()

    def _label_half_extents(self) -> tuple[float, float]:
        half = self.model.half_side()
        return half, half

    def _refresh_label(self) -> None:
        """Show the marker ID beside the square."""
        self._set_label_text("", str(self.model.marker_id))
        self._layout_labels()

    def set_side(self, side: float) -> None:
        """Update model side length and rebuild the square path."""
        self.model.side = side
        self._update_path()

    def _update_path(self) -> None:
        """Rebuild path geometry from the square side length."""
        half = max(self.model.side, 0.0) / 2.0
        kind, x, y, w, h = contact_path_box("square", half, 0.0)
        path = QPainterPath()
        if kind == "ellipse":
            path.addEllipse(x, y, w, h)
        else:
            path.addRect(x, y, w, h)
        self.setPath(path)
        if hasattr(self, "_view_labels"):
            self._layout_labels()

    def _refresh_style(self) -> None:
        """White fill; yellow when selected. Marker ID stays readable on the canvas."""
        if self.isSelected():
            fill = QColor("#ffd447")
            outline = QColor("#f6f7f8")
        else:
            fill = QColor(ORIENTATION_MARKER_FILL)
            outline = QColor(ORIENTATION_MARKER_OUTLINE)
        self.setBrush(QBrush(fill))
        self.setPen(QPen(outline, 2))
        outside = QBrush(LABEL_ON_DARK)
        pairs = getattr(self, "_view_labels", None)
        if pairs:
            for pair in pairs:
                pair.set_brushes(outside, outside)

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
        self.set_side(self.model.side)
        self._refresh_label()
        self._refresh_style()
