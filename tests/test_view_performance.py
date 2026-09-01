"""Performance helpers: overlay labels, axis subsample, pad links as overlay."""

from __future__ import annotations

import unittest

from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import QApplication

from mea_editor.electrode import Electrode
from mea_editor.electrode_array_view import (
    LABEL_MIN_CONTACT_PX,
    MAP_LABEL_FONT_POINT,
    overlay_label_parts,
    subsample_axis_positions,
)
from mea_editor.electrode_view import ElectrodeView
from mea_editor.pad import Pad
from mea_editor.pad_view import PadView


class AxisSubsampleTests(unittest.TestCase):
    def test_keeps_values_at_least_min_spacing_apart(self) -> None:
        values = [0.0, 0.5, 1.0, 1.2, 5.0]
        kept = subsample_axis_positions(values, lambda v: v * 10.0, min_spacing_px=8.0)
        self.assertEqual(kept, [0.0, 1.0, 5.0])

    def test_clips_to_visible_range(self) -> None:
        values = [-10.0, 0.0, 3.0, 20.0]
        kept = subsample_axis_positions(
            values, lambda v: v, min_spacing_px=1.0, lo=0.0, hi=10.0
        )
        self.assertEqual(kept, [0.0, 3.0])


class OverlayLabelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def _metrics(self) -> QFontMetrics:
        font = QFont()
        font.setPointSize(MAP_LABEL_FONT_POINT)
        return QFontMetrics(font)

    def test_contact_has_no_label_child_items(self) -> None:
        electrode = Electrode(eid=1, x=0.0, y=0.0, radius=12.0, intan_id="A-000")
        item = ElectrodeView(electrode, lambda: None, lambda: None)
        self.assertEqual(item.childItems(), [])

    def test_hides_labels_when_contact_is_tiny_on_screen(self) -> None:
        electrode = Electrode(eid=1, x=0.0, y=0.0, radius=12.0, intan_id="A-000")
        item = ElectrodeView(electrode, lambda: None, lambda: None)
        metrics = self._metrics()
        tiny_scale = (LABEL_MIN_CONTACT_PX / (12.0 * 2.0)) * 0.5
        self.assertEqual(overlay_label_parts(item, tiny_scale, metrics), [])
        parts = overlay_label_parts(item, 4.0, metrics)
        self.assertTrue(any(part.is_center for part in parts))
        self.assertTrue(any(not part.is_center for part in parts))


class PadLinkOverlayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def test_pad_view_does_not_add_a_scene_line_item(self) -> None:
        electrode = Electrode(eid=1, x=0.0, y=0.0)
        pad = Pad(pad_id=1, electrode_eid=1, x=40.0, y=0.0)
        item = PadView(pad, lambda: None, lambda: None, lambda eid: electrode)
        self.assertFalse(hasattr(item, "link_item"))
        item.update_link()
        self.assertEqual(item.childItems(), [])
