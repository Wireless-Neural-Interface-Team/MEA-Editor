"""Wheel zoom must stay usable after a tight fit (especially the pad camera)."""

from __future__ import annotations

import unittest

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication, QGraphicsScene

from mea_editor.electrode_array_view import (
    ZOOM_MAX_SCALE,
    ZOOM_MIN_SCALE,
    ElectrodeArrayView,
    clamp_zoom_factor,
    grow_scene_rect_to_include,
)


def _wheel(view: ElectrodeArrayView, delta_y: int) -> None:
    pos = QPointF(view.viewport().rect().center())
    global_pos = QPointF(view.mapToGlobal(pos.toPoint()))
    event = QWheelEvent(
        pos,
        global_pos,
        QPoint(0, 0),
        QPoint(0, delta_y),
        Qt.NoButton,
        Qt.NoModifier,
        Qt.ScrollPhase.ScrollUpdate,
        False,
    )
    view.wheelEvent(event)


class ClampZoomFactorTests(unittest.TestCase):
    def test_zoom_in_from_below_legacy_min_is_allowed(self) -> None:
        factor = clamp_zoom_factor(0.007, 1.15)
        self.assertIsNotNone(factor)
        self.assertGreater(factor, 1.0)

    def test_zoom_out_from_a_typical_pad_fit_scale_is_allowed(self) -> None:
        factor = clamp_zoom_factor(0.007, 1 / 1.15)
        self.assertIsNotNone(factor)
        self.assertLess(factor, 1.0)

    def test_overshoot_is_clamped_to_the_floor_instead_of_ignored(self) -> None:
        current = ZOOM_MIN_SCALE * 1.05
        factor = clamp_zoom_factor(current, 1 / 1.15)
        self.assertIsNotNone(factor)
        self.assertAlmostEqual(current * factor, ZOOM_MIN_SCALE, places=12)

    def test_blocked_only_at_the_true_floor(self) -> None:
        self.assertIsNone(clamp_zoom_factor(ZOOM_MIN_SCALE, 1 / 1.15))

    def test_blocked_only_at_the_true_ceiling(self) -> None:
        self.assertIsNone(clamp_zoom_factor(ZOOM_MAX_SCALE, 1.15))


class GrowSceneRectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def test_grows_scene_without_moving_the_other_camera(self) -> None:
        scene = QGraphicsScene()
        scene.setSceneRect(QRectF(-10.0, -10.0, 20.0, 20.0))
        left = ElectrodeArrayView(scene)
        right = ElectrodeArrayView(scene)
        left.resize(240, 240)
        right.resize(240, 240)
        left.show()
        right.show()
        self._app.processEvents()
        left.fit_scene_rect(QRectF(-5.0, -5.0, 10.0, 10.0))
        right.fit_scene_rect(QRectF(-5.0, -5.0, 10.0, 10.0))
        right_center = right.capture_camera()
        grow_scene_rect_to_include(scene, QRectF(-400.0, -400.0, 800.0, 800.0))
        restored = right.capture_camera()
        self.assertAlmostEqual(restored.x(), right_center.x(), places=2)
        self.assertAlmostEqual(restored.y(), right_center.y(), places=2)
        self.assertTrue(scene.sceneRect().contains(QRectF(-400.0, -400.0, 800.0, 800.0)))
        left.close()
        right.close()


class WheelZoomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(QRectF(-50.0, -50.0, 100.0, 100.0))
        self.view = ElectrodeArrayView(self.scene)
        self.other = ElectrodeArrayView(self.scene)
        self.scene.electrode_map_view = self.view
        self.scene.pad_map_view = self.other
        self.view.resize(400, 400)
        self.other.resize(400, 400)
        self.view.show()
        self.other.show()
        self._app.processEvents()

    def tearDown(self) -> None:
        self.view.close()
        self.other.close()

    def _set_scale(self, scale: float) -> None:
        self.view.resetTransform()
        self.view.scale(scale, -scale)

    def test_pad_like_fit_scale_can_zoom_in_and_out(self) -> None:
        self._set_scale(0.007)
        start = abs(self.view.transform().m11())
        _wheel(self.view, 120)
        zoomed_in = abs(self.view.transform().m11())
        self.assertGreater(zoomed_in, start)
        _wheel(self.view, -120)
        _wheel(self.view, -120)
        zoomed_out = abs(self.view.transform().m11())
        self.assertLess(zoomed_out, start)

    def test_electrode_view_can_zoom_out_past_the_legacy_floor(self) -> None:
        self._set_scale(0.05)
        for _ in range(24):
            _wheel(self.view, -120)
        zoomed_out = abs(self.view.transform().m11())
        self.assertLess(zoomed_out, 0.02)
        self.assertGreaterEqual(zoomed_out, ZOOM_MIN_SCALE)


if __name__ == "__main__":
    unittest.main()
