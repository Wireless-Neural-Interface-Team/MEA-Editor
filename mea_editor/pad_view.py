"""
Interactive graphics item bound to one Pad model.

It owns:
- contact shape path (circle, square, or rect),
- center / bottom labels copied from the associated electrode
  (shank + Potentiostat ID, INTAN ID) — pads have no numbers of their own,
- dashed link line toward the associated electrode.
"""

from __future__ import annotations

from typing import Callable

try:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QBrush, QColor, QFont, QPainterPath, QPen, QTransform
    from PySide6.QtWidgets import (
        QGraphicsItem,
        QGraphicsLineItem,
        QGraphicsPathItem,
        QGraphicsSimpleTextItem,
    )
except ImportError as exc:
    raise SystemExit("PySide6 is required. Install with: pip install PySide6") from exc

from .contact_shape import contact_half_extents, contact_path_box
from .electrode import Electrode
from .pad import Pad


class PadView(QGraphicsPathItem):
    """
    Interactive graphics item bound to one `Pad` model.

    Pads are drawn as circle, square, or rect according to `model.shape`.
    """

    def __init__(
        self,
        model: Pad,
        on_change,
        on_selection_change,
        get_electrode: Callable[[int], Electrode | None],
    ) -> None:
        super().__init__()
        self.model = model
        self._on_change = on_change
        self._on_selection_change = on_selection_change
        self._get_electrode = get_electrode
        self.setFlags(
            QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setZValue(9)

        self.link_item = QGraphicsLineItem()
        self.link_item.setZValue(5)
        self.link_item.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.link_item.setFlag(QGraphicsItem.ItemIsFocusable, False)
        self.link_item.setAcceptedMouseButtons(Qt.NoButton)

        label_font = QFont()
        label_font.setPointSize(9)
        self.label = QGraphicsSimpleTextItem("", self)
        self.label.setBrush(QBrush(QColor("#e9edf2")))
        self.label.setFont(label_font)
        self.label.setTransform(QTransform.fromScale(1.0, 1.0))
        self.label.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.contact_label = QGraphicsSimpleTextItem("", self)
        self.contact_label.setBrush(QBrush(QColor("#d3dbe4")))
        self.contact_label.setFont(label_font)
        self.contact_label.setTransform(QTransform.fromScale(1.0, 1.0))
        self.contact_label.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self._refresh_label()
        self.set_radius(model.radius)
        self.setPos(model.x, model.y)
        self._layout_labels()
        self._refresh_style()
        self.update_link()

    def _refresh_label(self) -> None:
        """
        Sync labels from the associated electrode (no pad numbers).

        Center: shank + Potentiostat ID. Below: INTAN ID.
        """
        electrode = self._get_electrode(self.model.electrode_eid)
        if electrode is None:
            self.label.setText("?")
            self.contact_label.setText("")
        else:
            self.label.setText(electrode.map_center_label())
            self.contact_label.setText(str(electrode.intan_id))
        self._layout_labels()

    def _view_scale(self) -> float:
        """Get the view's scale factor (scene units per pixel) for label positioning."""
        scene = self.scene()
        if scene is None:
            return 1.0
        if hasattr(scene, "view_scale"):
            return scene.view_scale(getattr(scene, "pad_map_view", None))
        views = scene.views()
        if not views:
            return 1.0
        t = views[0].transform()
        scale = abs(t.m11()) if t.m11() != 0 else 1.0
        return max(scale, 1e-6)

    def _layout_labels(self) -> None:
        """Position labels: electrode Potentiostat/shank at center, INTAN ID below."""
        scale = self._view_scale()
        br = self.label.boundingRect()
        label_w, label_h = br.width() / scale, br.height() / scale
        self.label.setPos(-label_w / 2, label_h / 2)
        cbr = self.contact_label.boundingRect()
        contact_h = cbr.height() / scale
        _half_x, half_y = contact_half_extents(self.model.shape, self.model.radius, self.model.height)
        y_offset = half_y + contact_h + 4.0
        contact_w = cbr.width() / scale
        self.contact_label.setPos(-contact_w / 2, y_offset)

    def set_radius(self, radius: float) -> None:
        """Update model radius and rebuild the pad path."""
        self.model.radius = radius
        self._update_path()

    def set_height(self, height: float) -> None:
        """Update model height and rebuild the pad path."""
        self.model.height = height
        self._update_path()

    def _update_path(self) -> None:
        """Rebuild path geometry from the pad shape, radius, and height."""
        kind, x, y, w, h = contact_path_box(self.model.shape, self.model.radius, self.model.height)
        path = QPainterPath()
        if kind == "ellipse":
            path.addEllipse(x, y, w, h)
        else:
            path.addRect(x, y, w, h)
        self.setPath(path)
        if hasattr(self, "label") and hasattr(self, "contact_label"):
            self._layout_labels()

    def _has_valid_electrode(self) -> bool:
        return self._get_electrode(self.model.electrode_eid) is not None

    def _refresh_style(self) -> None:
        """
        Apply fill and outline colors based on state.

        Priority: pairing/duplicate error (red) > selected (yellow) >
        enabled (purple) > disabled (gray).
        """
        is_error = self.model.has_any_duplicate() or not self._has_valid_electrode()
        if is_error:
            fill = QColor("#d44b4b")
            outline = QColor("#ffe0e0")
            pen = QPen(outline, 2)
        elif self.isSelected():
            fill = QColor("#ffd447")
            outline = QColor("#f6f7f8")
            pen = QPen(outline, 2)
        elif self.model.enabled:
            fill = QColor("#c77dff")
            outline = QColor("#232b35")
            pen = QPen(outline, 2)
        else:
            fill = QColor("#4f5761")
            outline = QColor("#232b35")
            pen = QPen(outline, 2)
        self.setBrush(QBrush(fill))
        self.setPen(pen)
        link_pen = QPen(QColor("#9fb3c8"), 1, Qt.DashLine)
        link_pen.setCosmetic(True)
        self.link_item.setPen(link_pen)

    def update_link(self) -> None:
        """Update the dashed line toward the associated electrode."""
        electrode = self._get_electrode(self.model.electrode_eid)
        if electrode is None:
            self.link_item.setVisible(False)
            return
        self.link_item.setVisible(True)
        self.link_item.setLine(self.model.x, self.model.y, electrode.x, electrode.y)

    def itemChange(self, change, value):  # type: ignore[override]
        """Copy x/y to model on move; refresh style and panel on selection."""
        if change == QGraphicsItem.ItemPositionHasChanged:
            p = self.pos()
            self.model.x = p.x()
            self.model.y = p.y()
            self.update_link()
            self._on_change()
        elif change == QGraphicsItem.ItemSelectedHasChanged:
            self._refresh_style()
            self._on_selection_change()
        return super().itemChange(change, value)

    def sync_from_model(self) -> None:
        """Apply model state to visual item."""
        self.setPos(self.model.x, self.model.y)
        self.set_radius(self.model.radius)
        self._refresh_label()
        self._refresh_style()
        self.update_link()
