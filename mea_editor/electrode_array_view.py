"""
Interactive viewport for the electrode scene.

Responsibilities:
- pan/zoom behavior and mouse interactions,
- add-mode click handling,
- drawing dynamic grid/axis overlays.
"""

from __future__ import annotations

try:
    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QTransform
    from PySide6.QtWidgets import (
        QFrame,
        QGraphicsItem,
        QGraphicsScene,
        QGraphicsSimpleTextItem,
        QGraphicsView,
        QStyle,
        QStyleOptionGraphicsItem,
    )
except ImportError as exc:
    raise SystemExit("PySide6 is required. Install with: pip install PySide6") from exc

from .contact_shape import contact_half_extents
from .electrode import (
    DEFAULT_LABEL_ORIENTATION,
    DEFAULT_LABEL_POSITION,
    map_label_item_pos,
    normalize_label_orientation,
    normalize_label_position,
)

# Overlay axis band dimensions (in viewport pixels).
AXIS_BAND_HEIGHT = 24
AXIS_BAND_WIDTH = 52
# Min pixel distance between axis tick labels to avoid overlap.
GRID_MIN_LABEL_SPACING_PX = 44
# Keep contact labels inside the plot area when fitting.
FIT_LABEL_MARGIN_PX = 42.0
ZOOM_MIN_SCALE = 0.02
ZOOM_MAX_SCALE = 80.0
MAP_VIEW_ATTRS = ("electrode_map_view", "pad_map_view")


def _option_without_qt_selection(option):
    """Copy a paint option without Qt's default selection overlay.

    QGraphicsPathItem / QGraphicsSimpleTextItem otherwise draw a dashed
    rectangle around exposedRect. With ItemIgnoresTransformations labels
    or a rubber-band update region, that rect can cover a whole column
    and show up as a white bar on the dark canvas.
    """
    opt = QStyleOptionGraphicsItem(option)
    opt.state &= ~QStyle.State_Selected
    return opt


class ViewScopedTextItem(QGraphicsSimpleTextItem):
    """
    Contact label that paints in only one mapping view.

    Electrodes and pads share one scene shown by two cameras. Labels use
    ItemIgnoresTransformations, so screen size is correct for a single zoom.
    Each contact keeps one copy per camera; this item paints only in its home
    view so the other camera can keep an independently positioned copy.
    """

    def __init__(self, text: str = "", parent=None, view_attr: str = "") -> None:
        super().__init__(text, parent)
        self._view_attr = view_attr
        self.setAcceptedMouseButtons(Qt.NoButton)

    def paint(self, painter, option, widget=None) -> None:  # type: ignore[override]
        if widget is not None and not self._is_home_viewport(widget):
            return
        super().paint(painter, _option_without_qt_selection(option), widget)

    def _is_home_viewport(self, widget) -> bool:
        scene = self.scene()
        if scene is None or not self._view_attr:
            return True
        view = getattr(scene, self._view_attr, None)
        if view is None:
            return True
        viewport = view.viewport()
        current = widget
        while current is not None:
            if current is view or current is viewport:
                return True
            current = current.parentWidget()
        return False


def _make_scoped_label(parent, view_attr: str, font: QFont, color: str) -> ViewScopedTextItem:
    item = ViewScopedTextItem("", parent, view_attr)
    item.setBrush(QBrush(QColor(color)))
    item.setFont(font)
    item.setTransform(QTransform.fromScale(1.0, 1.0))
    item.setFlag(QGraphicsItem.ItemIgnoresTransformations)
    return item


class ViewLabelPair:
    """Center + outside labels laid out for one mapping camera."""

    def __init__(self, parent, view_attr: str, font: QFont) -> None:
        self.view_attr = view_attr
        self.center = _make_scoped_label(parent, view_attr, font, "#e9edf2")
        self.below = _make_scoped_label(parent, view_attr, font, "#ffffff")

    def set_text(self, center: str, below: str) -> None:
        self.center.setText(center)
        self.below.setText(below)
        self.center.setVisible(bool(center))
        self.below.setVisible(bool(below))

    def set_brushes(self, center: QBrush, below: QBrush) -> None:
        self.center.setBrush(center)
        self.below.setBrush(below)

    def layout(
        self,
        scale: float,
        half_x: float,
        half_y: float,
        position: str,
        orientation: int = DEFAULT_LABEL_ORIENTATION,
    ) -> None:
        br = self.center.boundingRect()
        label_w, label_h = br.width() / scale, br.height() / scale
        self.center.setRotation(0)
        self.center.setPos(-label_w / 2, label_h / 2)
        cbr = self.below.boundingRect()
        text_w, text_h = cbr.width() / scale, cbr.height() / scale
        degrees = normalize_label_orientation(orientation)
        self.below.setRotation(degrees)
        x, y = map_label_item_pos(
            position, half_x, half_y, text_w, text_h, orientation=degrees
        )
        self.below.setPos(x, y)


class PerViewContactLabels:
    """
    Two label copies per contact, one per mapping camera.

    Zooming one view only relayouts that view's copies, so text in the other
    view stays put.
    """

    def _init_view_labels(self) -> None:
        font = QFont()
        font.setPointSize(9)
        self._view_labels = [ViewLabelPair(self, attr, font) for attr in MAP_VIEW_ATTRS]
        self.label = self._view_labels[0].center
        self.contact_label = self._view_labels[0].below

    def _set_label_text(self, center: str, below: str) -> None:
        for pair in self._view_labels:
            pair.set_text(center, below)

    def _view_scale(self, view_attr: str) -> float:
        scene = self.scene()
        if scene is None:
            return 1.0
        if hasattr(scene, "view_scale"):
            return scene.view_scale(getattr(scene, view_attr, None))
        views = scene.views()
        if not views:
            return 1.0
        t = views[0].transform()
        scale = abs(t.m11()) if t.m11() != 0 else 1.0
        return max(scale, 1e-6)

    def _label_half_extents(self) -> tuple[float, float]:
        return contact_half_extents(self.model.shape, self.model.radius, self.model.height)

    def _layout_labels(self, view_attr: str | None = None) -> None:
        half_x, half_y = self._label_half_extents()
        position = normalize_label_position(
            getattr(self.model, "label_position", DEFAULT_LABEL_POSITION)
        )
        orientation = normalize_label_orientation(
            getattr(self.model, "label_orientation", DEFAULT_LABEL_ORIENTATION)
        )
        for pair in self._view_labels:
            if view_attr is not None and pair.view_attr != view_attr:
                continue
            pair.layout(
                self._view_scale(pair.view_attr), half_x, half_y, position, orientation
            )

    def paint(self, painter, option, widget=None) -> None:  # type: ignore[override]
        super().paint(painter, _option_without_qt_selection(option), widget)


class ElectrodeArrayView(QGraphicsView):
    """
    Interactive viewport for the electrode scene.

    Responsibilities:
    - pan/zoom behavior and mouse interactions,
    - add-mode click handling,
    - drawing dynamic grid/axis overlays.
    """

    def __init__(self, scene: QGraphicsScene) -> None:
        """
        Initialize the graphics view for the electrode scene.

        Args:
            scene: Qt scene containing items (electrodes, grid).
        """
        super().__init__(scene)
        # Antialiasing improves circle and text rendering quality.
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setFrameShape(QFrame.NoFrame)
        # Keep content centered when the transformed scene is smaller than the view.
        self.setAlignment(Qt.AlignCenter)
        # Rubber-band drag enables box selection on empty area.
        self.setDragMode(QGraphicsView.RubberBandDrag)
        # Full redraw avoids leftover rubber-band edges and overlay artifacts.
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setBackgroundBrush(QColor("#11151a"))
        # Cartesian orientation for scene coordinates: Y grows upward.
        # Qt view Y is naturally downward; scale(1,-1) flips it.
        self.scale(1.0, -1.0)
        # Pan is middle-drag; hiding scrollbars keeps the viewport size
        # stable so fit/center is not shifted by a late scrollbar.
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._is_add_mode = lambda: False
        self._add_at = lambda x, y: None
        self._on_delete = lambda: None
        self._on_view_transform_changed = lambda view=None: None
        self._on_activated = lambda: None
        self._is_middle_panning = False
        self._last_pan_pos = None

    def set_add_callbacks(self, is_add_mode, add_at) -> None:
        """
        Register callbacks for add-point mode (electrode or pad).

        Args:
            is_add_mode: Function returning True if add mode is active.
            add_at: Function(x, y) creating a point at the given position.
        """
        self._is_add_mode = is_add_mode
        self._add_at = add_at

    def set_delete_callback(self, on_delete) -> None:
        """
        Register callback for delete-selected action (Suppr/Backspace).
        """
        self._on_delete = on_delete

    def set_view_transform_changed_callback(self, on_changed) -> None:
        """
        Register callback when view zoom/pan changes (for label layout refresh).
        """
        self._on_view_transform_changed = on_changed

    def set_activated_callback(self, on_activated) -> None:
        """Register callback when this viewport is clicked or zoomed."""
        self._on_activated = on_activated

    def capture_camera(self) -> QPointF:
        """Scene point currently shown at the viewport center."""
        return self.mapToScene(self.viewport().rect().center())

    def restore_camera(self, scene_center: QPointF) -> None:
        """Keep `scene_center` at the viewport center after a scene-rect change."""
        current = self.mapFromScene(scene_center)
        target = self.viewport().rect().center()
        self.horizontalScrollBar().setValue(
            int(round(self.horizontalScrollBar().value() + current.x() - target.x()))
        )
        self.verticalScrollBar().setValue(
            int(round(self.verticalScrollBar().value() + current.y() - target.y()))
        )

    def visible_scene_rect(self) -> QRectF:
        """Axis-aligned scene rect currently shown in this viewport."""
        return self.mapToScene(self.viewport().rect()).boundingRect()

    def fit_scene_rect(self, rect: QRectF) -> None:
        """
        Frame `rect` in the plot area (viewport minus axis bands), Y-up.

        `QGraphicsView.fitInView` uses the full viewport, then a scrollbar
        nudge for the axis bands. That nudge is clamped when the framed
        rect is almost as large as the scene (typical for pads), so the
        view ends up off-center. This fits and centers in the usable area.
        """
        if rect.width() <= 0 or rect.height() <= 0:
            return

        prev_size = None
        for _ in range(4):
            vp = self.viewport().rect()
            size = (vp.width(), vp.height())
            if size[0] <= 1 or size[1] <= 1:
                return
            if size == prev_size:
                break
            prev_size = size

            axis_w = float(AXIS_BAND_WIDTH)
            axis_h = float(AXIS_BAND_HEIGHT)
            usable_w = max(vp.width() - axis_w, 1.0)
            usable_h = max(vp.height() - axis_h, 1.0)

            def scale_to_fit(framed: QRectF) -> float:
                return min(
                    usable_w / max(framed.width(), 1e-9),
                    usable_h / max(framed.height(), 1e-9),
                )

            scale = scale_to_fit(rect)
            label_pad = FIT_LABEL_MARGIN_PX / max(scale, 1e-9)
            framed = rect.adjusted(-label_pad, -label_pad, label_pad, label_pad)
            scale = scale_to_fit(framed)

            self.resetTransform()
            self.scale(scale, -scale)
            target = QPointF(axis_w + usable_w / 2.0, axis_h + usable_h / 2.0)
            current = self.mapFromScene(framed.center())
            self.horizontalScrollBar().setValue(
                int(round(self.horizontalScrollBar().value() + current.x() - target.x()))
            )
            self.verticalScrollBar().setValue(
                int(round(self.verticalScrollBar().value() + current.y() - target.y()))
            )

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        """
        Handle mouse click: add mode, pan, or selection.
        """
        self._on_activated()
        # Middle button drag pans the view.
        if event.button() == Qt.MiddleButton:
            self._is_middle_panning = True
            self._last_pan_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return

        # Left button only.
        if event.button() == Qt.LeftButton:
            # In add mode, left-click creates an electrode, pad, or orientation marker.
            if self._is_add_mode():
                scene_pos = self.mapToScene(event.pos())
                self._add_at(scene_pos.x(), scene_pos.y())
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        """
        While middle button is held, pan by translating scrollbars.
        """
        if self._is_middle_panning and self._last_pan_pos is not None:
            delta = event.pos() - self._last_pan_pos
            self._last_pan_pos = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        """
        End middle-button pan, then let Qt finish the click (selection).
        """
        if event.button() == Qt.MiddleButton and self._is_middle_panning:
            self._is_middle_panning = False
            self._last_pan_pos = None
            self.unsetCursor()
            event.accept()
            return

        super().mouseReleaseEvent(event)
        if event.button() == Qt.LeftButton:
            self.viewport().update()

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        """
        Handle Suppr/Backspace to delete selected electrodes when view has focus.
        """
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self._on_delete()
            event.accept()
            return
        super().keyPressEvent(event)

    def wheelEvent(self, event) -> None:  # type: ignore[override]
        """
        Zoom centered on cursor: the point under the mouse stays fixed.

        Store scene point under cursor, apply scale, then adjust scrollbars
        so that point remains under the cursor.
        """
        self._on_activated()
        # event.position() is Qt6; event.pos() fallback for older APIs.
        try:
            mouse_pos = event.position().toPoint()
        except AttributeError:
            mouse_pos = event.pos()

        # Remember which scene point is under the cursor before scaling.
        scene_pos_before = self.mapToScene(mouse_pos)
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        current = abs(self.transform().m11())
        new_scale = current * factor
        if new_scale < ZOOM_MIN_SCALE or new_scale > ZOOM_MAX_SCALE:
            event.accept()
            return
        self.scale(factor, factor)

        # After scale, that scene point moved in viewport; adjust scrollbars
        # so it stays under the cursor (zoom appears centered on mouse).
        viewport_pos_after = self.mapFromScene(scene_pos_before)
        delta_view = viewport_pos_after - mouse_pos
        self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() + delta_view.x())
        self.verticalScrollBar().setValue(self.verticalScrollBar().value() + delta_view.y())

        # Relayout this camera's label copies only; the other view is unchanged.
        self._on_view_transform_changed(self)

    def scrollContentsBy(self, dx: int, dy: int) -> None:  # type: ignore[override]
        """
        Force overlay repaint when panning with scrollbars.

        Without this, axis bands would stay fixed during scroll.
        """
        super().scrollContentsBy(dx, dy)
        scene = self.scene()
        if scene is not None:
            scene.invalidate(
                scene.sceneRect(),
                QGraphicsScene.BackgroundLayer | QGraphicsScene.ForegroundLayer,
            )
        self.viewport().update()

    def drawBackground(self, painter: QPainter, rect) -> None:  # type: ignore[override]
        """
        Draw grid lines in scene coordinates.

        X/Y positions come from electrodes via scene.get_axes().
        Vertical lines follow X values, horizontal lines follow Y values.
        """
        super().drawBackground(painter, rect)
        scene = self.scene()
        if scene is None or not hasattr(scene, "get_axes"):
            return
        # Axes come from unique electrode X/Y; grid follows electrode layout.
        xs, ys = scene.get_axes(self)  # type: ignore[attr-defined]
        if not xs and not ys:
            return
        grid_pen = QPen(QColor("#3b4f66"))
        grid_pen.setWidthF(0)  # Cosmetic width: 1 logical pixel.
        painter.setPen(grid_pen)
        for x in xs:
            painter.drawLine(x, rect.top(), x, rect.bottom())
        for y in ys:
            painter.drawLine(rect.left(), y, rect.right(), y)

    def drawForeground(self, painter: QPainter, rect) -> None:  # type: ignore[override]
        """
        Draw fixed overlays (axis bands + numeric ticks).

        In viewport coordinates to stay fixed on screen during zoom/pan.
        """
        super().drawForeground(painter, rect)
        scene = self.scene()
        if scene is None or not hasattr(scene, "get_axes"):
            return

        xs, ys = scene.get_axes(self)  # type: ignore[attr-defined]
        if not xs and not ys:
            return

        painter.save()
        # Draw overlays in viewport coordinates (fixed on screen).
        painter.resetTransform()

        vp = self.viewport().rect()
        axis_h = AXIS_BAND_HEIGHT
        axis_w = AXIS_BAND_WIDTH

        # Dark bands for axis labels (top horizontal, left vertical).
        painter.fillRect(0, 0, vp.width(), axis_h, QColor("#0f1318"))
        painter.fillRect(0, 0, axis_w, vp.height(), QColor("#0f1318"))

        # Separator lines between axis bands and plot area.
        sep_pen = QPen(QColor("#3b4f66"))
        painter.setPen(sep_pen)
        painter.drawLine(axis_w, 0, axis_w, vp.height())
        painter.drawLine(0, axis_h, vp.width(), axis_h)

        # Axis labels: Y bottom-left, X top-left of plot area.
        painter.setPen(QColor("#9fb3c8"))
        baseline_y = vp.height() - 8
        painter.drawText(6, baseline_y, "Y")
        painter.drawText(axis_w + 6, 16, "X")

        # X ticks: skip if outside visible area or too close to previous label.
        min_px_spacing = GRID_MIN_LABEL_SPACING_PX
        last_x_px = -10_000
        for x in xs:
            px = self.mapFromScene(x, 0).x()
            if px < axis_w or px > vp.width() - 2:
                continue
            if px - last_x_px < min_px_spacing:
                continue
            last_x_px = px
            painter.setPen(QColor("#6e88a5"))
            painter.drawLine(px, axis_h - 6, px, axis_h)
            painter.setPen(QColor("#d3dbe4"))
            painter.drawText(px + 3, 16, f"{x:.1f}")

        # Y ticks: same logic; abs() needed because Y may increase upward or down.
        last_y_px = -10_000
        for y in ys:
            py = self.mapFromScene(0, y).y()
            if py < axis_h or py > vp.height() - 2:
                continue
            if abs(py - last_y_px) < min_px_spacing:
                continue
            last_y_px = py
            painter.setPen(QColor("#6e88a5"))
            painter.drawLine(axis_w - 6, py, axis_w, py)
            painter.setPen(QColor("#d3dbe4"))
            painter.drawText(4, py - 3, f"{y:.1f}")

        painter.restore()
