"""Selected contacts must not draw Qt's default white selection rectangle."""

from __future__ import annotations

import unittest

from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsScene,
    QStyle,
    QStyleOptionGraphicsItem,
)

from mea_editor.electrode import Electrode
from mea_editor.electrode_array_view import _option_without_qt_selection
from mea_editor.electrode_view import ElectrodeView
from mea_editor.orientation_marker import OrientationMarker
from mea_editor.orientation_marker_view import OrientationMarkerView
from mea_editor.pad import Pad
from mea_editor.pad_view import PadView


class SelectionOverlayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def test_helper_clears_selected_state(self) -> None:
        option = QStyleOptionGraphicsItem()
        option.state = QStyle.State_Selected | QStyle.State_Enabled
        cleared = _option_without_qt_selection(option)
        self.assertFalse(bool(cleared.state & QStyle.State_Selected))
        self.assertTrue(bool(cleared.state & QStyle.State_Enabled))

    def test_selected_contacts_paint_without_error(self) -> None:
        scene = QGraphicsScene()
        electrode = Electrode(eid=1, x=0.0, y=0.0)
        item = ElectrodeView(electrode, lambda: None, lambda: None)
        scene.addItem(item)
        item.setSelected(True)

        pad = Pad(pad_id=1, electrode_eid=1, x=10.0, y=0.0)
        pad_item = PadView(pad, lambda: None, lambda: None, lambda eid: electrode)
        scene.addItem(pad_item)
        pad_item.setSelected(True)

        marker = OrientationMarker(marker_id=1, x=20.0, y=0.0, radius=8.0)
        marker_item = OrientationMarkerView(marker, lambda: None, lambda: None)
        scene.addItem(marker_item)
        marker_item.setSelected(True)

        image = QImage(64, 64, QImage.Format_ARGB32)
        painter = QPainter(image)
        option = QStyleOptionGraphicsItem()
        option.state = QStyle.State_Selected
        option.exposedRect = item.boundingRect()
        item.paint(painter, option, None)
        pad_item.paint(painter, option, None)
        marker_item.paint(painter, option, None)
        painter.end()
