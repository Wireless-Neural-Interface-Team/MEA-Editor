"""
Interactive graphics item bound to one Pad model.

It owns:
- contact shape path (circle, square, or rect),
- center / outside map-label text from the associated electrode
  (drawn by the mapping view overlay),
- fill color that varies by the linked electrode's shank (purples).
"""

from __future__ import annotations

from typing import Callable

try:
    from PySide6.QtGui import QColor, QPainterPath
    from PySide6.QtWidgets import (
        QGraphicsItem,
        QGraphicsPathItem,
    )
except ImportError as exc:
    raise SystemExit("PySide6 is required. Install with: pip install PySide6") from exc

from .contact_shape import contact_path_box
from .electrode import Electrode
from .electrode_array_view import PerViewContactLabels
from .pad import Pad
from .view_style import apply_contact_colors, pad_fill_for_shank

MapLabelFn = Callable[[Electrode], tuple[str, str]]


class PadView(PerViewContactLabels, QGraphicsPathItem):
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
        map_labels: MapLabelFn | None = None,
    ) -> None:
        super().__init__()
        self.model = model
        self._on_change = on_change
        self._on_selection_change = on_selection_change
        self._get_electrode = get_electrode
        self._map_labels = map_labels
        self.setFlags(
            QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setZValue(9)
        self.setAcceptHoverEvents(False)

        self._init_view_labels()
        self._refresh_label()
        self.set_radius(model.radius)
        self.setPos(model.x, model.y)
        self._refresh_style()
        self.update_link()

    def _refresh_label(self) -> None:
        """Sync labels from the associated electrode's visible IDs. Pad ID is not shown."""
        electrode = self._get_electrode(self.model.electrode_eid)
        if electrode is None:
            self._set_label_text("?", "?")
        elif self._map_labels is not None:
            center, below = self._map_labels(electrode)
            self._set_label_text(center, below)
        else:
            center, below = electrode.map_view_labels()
            self._set_label_text(center, below)

    def _color_for_shank(self) -> QColor:
        """Return a purple fill color that varies by the linked electrode's shank."""
        electrode = self._get_electrode(self.model.electrode_eid)
        shank = electrode.shank_id if electrode is not None else ""
        return pad_fill_for_shank(shank)

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

    def _has_valid_electrode(self) -> bool:
        return self._get_electrode(self.model.electrode_eid) is not None

    def _refresh_style(self) -> None:
        """
        Apply fill and outline colors based on state.

        Priority: pairing/duplicate error (red) > selected (yellow) >
        purple by shank. A selected red pad keeps its error fill and gets a
        thick yellow outline so the selection stays visible.
        """
        is_error = self.model.has_any_duplicate() or not self._has_valid_electrode()
        is_selected = self.isSelected()
        if is_error:
            if is_selected:
                apply_contact_colors(self, QColor("#d44b4b"), QColor("#ffd447"), 4)
            else:
                apply_contact_colors(self, QColor("#d44b4b"), QColor("#ffe0e0"))
        elif is_selected:
            apply_contact_colors(self, QColor("#ffd447"), QColor("#f6f7f8"))
        else:
            apply_contact_colors(self, self._color_for_shank())

    def update_link(self) -> None:
        """Pad-electrode lines are drawn by the pad mapping view, not scene items."""
        return

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
        self._refresh_label()
        self._refresh_style()
        self.update_link()
