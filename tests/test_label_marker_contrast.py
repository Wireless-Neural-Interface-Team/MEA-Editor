"""Outside map labels stay readable where they overlap a white orientation marker."""

from __future__ import annotations

import unittest

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import QApplication

from mea_editor.electrode import Electrode
from mea_editor.electrode_array_view import (
    ElectrodeArrayView,
    MAP_LABEL_FONT_POINT,
    overlay_label_parts,
)
from mea_editor.electrode_view import ElectrodeView
from mea_editor.grid_scene import GridScene
from mea_editor.orientation_marker import OrientationMarker
from mea_editor.orientation_marker_view import OrientationMarkerView


def _luminance(color) -> float:
    return 0.2126 * color.red() + 0.7152 * color.green() + 0.0722 * color.blue()


def _is_canvas(color) -> bool:
    return abs(color.red() - 17) < 8 and abs(color.green() - 21) < 8 and abs(color.blue() - 26) < 8


class LabelMarkerContrastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def test_outside_label_is_dark_on_marker_and_light_on_canvas(self) -> None:
        scene = GridScene()
        view = ElectrodeArrayView(scene)
        other = ElectrodeArrayView(scene)
        scene.electrode_map_view = view
        scene.pad_map_view = other
        scene.active_view = view

        electrode = Electrode(
            eid=1,
            x=0.0,
            y=0.0,
            intan_id="A-000",
            label_position="below",
        )
        electrode_item = ElectrodeView(electrode, lambda: None, lambda: None)
        scene.addItem(electrode_item)

        marker = OrientationMarker(marker_id=1, x=10.0, y=-16.0, radius=8.0, shape="square")
        marker_item = OrientationMarkerView(marker, lambda: None, lambda: None)
        scene.addItem(marker_item)
        scene.has_orientation_markers = True

        view.resize(480, 480)
        view.show()
        self._app.processEvents()
        view.fit_scene_rect(QRectF(-30.0, -40.0, 60.0, 70.0))
        self._app.processEvents()

        try:
            pixmap = view.viewport().grab()
            dpr = pixmap.devicePixelRatio()
            image = pixmap.toImage()
            font = QFont()
            font.setPointSize(MAP_LABEL_FONT_POINT)
            metrics = QFontMetrics(font)
            scale = abs(view.transform().m11())
            parts = overlay_label_parts(electrode_item, scale, metrics)
            below = next(part for part in parts if not part.is_center)
            self.assertTrue(below.contrast)
            origin = view.mapFromScene(electrode_item.mapToScene(below.item_pos))
            rect = QRectF(origin.x(), origin.y(), below.pixel_w, below.pixel_h)
            marker_from_view, ok = marker_item.deviceTransform(view.viewportTransform()).inverted()
            self.assertTrue(ok)
            self.assertGreater(rect.width(), 8)
            self.assertGreater(rect.height(), 6)

            light_on_canvas = 0
            dark_on_marker = 0
            for dx in range(int(rect.width())):
                for dy in range(int(rect.height())):
                    vx = rect.x() + dx
                    vy = rect.y() + dy
                    px = int(round(vx * dpr))
                    py = int(round(vy * dpr))
                    if not (0 <= px < image.width() and 0 <= py < image.height()):
                        continue
                    pixel = image.pixelColor(px, py)
                    on_marker = marker_item.path().contains(marker_from_view.map(QPointF(vx, vy)))
                    if on_marker:
                        if not _is_canvas(pixel) and _luminance(pixel) < 130:
                            dark_on_marker += 1
                    elif _luminance(pixel) > 180:
                        light_on_canvas += 1

            self.assertGreater(
                dark_on_marker,
                0,
                "expected dark inverted label pixels on the orientation marker",
            )
            self.assertGreater(
                light_on_canvas,
                0,
                "expected light inverted label pixels on the dark canvas",
            )
        finally:
            view.close()
            other.close()


if __name__ == "__main__":
    unittest.main()
