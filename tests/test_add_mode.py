"""Add-mode UI lock and pad-target electrode highlight."""

from __future__ import annotations

import unittest

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QGraphicsItem, QGraphicsView

from mea_editor.electrode import Electrode
from mea_editor.electrode_array_editor_qt import ElectrodeArrayEditorQt


class AddModeUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.editor = ElectrodeArrayEditorQt()
        self.editor._set_array(
            [
                Electrode(eid=0, x=0.0, y=0.0),
                Electrode(eid=1, x=40.0, y=0.0),
            ],
            pads=[],
        )

    def tearDown(self) -> None:
        self.editor.is_dirty = False
        self.editor.close()

    def test_add_pad_mode_highlights_chosen_electrode(self) -> None:
        self.editor.pad_add_electrode_combo.setCurrentIndex(
            self.editor.pad_add_electrode_combo.findData(1)
        )
        self.editor.b_add_pad.setChecked(True)
        self.assertTrue(self.editor.is_add_pad_mode)
        self.assertTrue(self.editor.items[1].model.has_missing_pad)
        self.assertFalse(self.editor.items[0]._is_add_target)
        self.assertTrue(self.editor.items[1]._is_add_target)
        self.assertFalse(self.editor.items[1].isSelected())
        self.assertEqual(self.editor.items[1].brush().color(), QColor("#ffd447"))
        self.assertEqual(self.editor.items[0].brush().color(), QColor("#d44b4b"))

        self.editor.b_add_pad.setChecked(False)
        self.assertFalse(self.editor.items[1]._is_add_target)
        self.assertEqual(self.editor.items[1].brush().color(), QColor("#d44b4b"))

    def test_add_pad_mode_locks_inspector_except_stop_button_and_views(self) -> None:
        self.editor.b_add_pad.setChecked(True)
        self.assertFalse(self.editor._array_group.isEnabled())
        self.assertFalse(self.editor._selection_group.isEnabled())
        self.assertFalse(self.editor.pad_add_electrode_combo.isEnabled())
        self.assertFalse(self.editor.point_tabs.tabBar().isEnabled())
        self.assertFalse(self.editor.menuBar().isEnabled())
        self.assertTrue(self.editor.b_add_pad.isEnabled())
        self.assertTrue(self.editor.electrode_view.isEnabled())
        self.assertTrue(self.editor.pads_map_view.isEnabled())
        self.assertEqual(self.editor.electrode_view.dragMode(), QGraphicsView.NoDrag)
        self.assertFalse(bool(self.editor.items[0].flags() & QGraphicsItem.ItemIsSelectable))

        self.editor.b_add_pad.setChecked(False)
        self.assertTrue(self.editor._array_group.isEnabled())
        self.assertTrue(self.editor.pad_add_electrode_combo.isEnabled())
        self.assertTrue(self.editor.menuBar().isEnabled())
        self.assertTrue(bool(self.editor.items[0].flags() & QGraphicsItem.ItemIsSelectable))
        self.assertEqual(self.editor.electrode_view.dragMode(), QGraphicsView.RubberBandDrag)

    def test_add_electrode_mode_locks_inspector_the_same_way(self) -> None:
        self.editor.b_add_electrode.setChecked(True)
        self.assertTrue(self.editor.is_add_mode)
        self.assertFalse(self.editor._array_group.isEnabled())
        self.assertTrue(self.editor.b_add_electrode.isEnabled())
        self.assertFalse(self.editor.b_add_pad.isEnabled())
        self.editor.b_add_electrode.setChecked(False)
        self.assertTrue(self.editor._array_group.isEnabled())

    def test_add_electrode_does_not_create_a_pad(self) -> None:
        self.assertEqual(len(self.editor.electrodes), 2)
        self.assertEqual(self.editor.pads, {})
        self.editor._add_electrode_at(80.0, 0.0)
        self.assertEqual(len(self.editor.electrodes), 3)
        self.assertEqual(self.editor.pads, {})
        self.assertIn(2, self.editor.electrodes)
        self.assertAlmostEqual(self.editor.electrodes[2].x, 80.0)
        self.assertAlmostEqual(self.editor.electrodes[2].y, 0.0)

    def test_placing_pad_keeps_highlight_on_next_free_electrode(self) -> None:
        self.editor.pad_add_electrode_combo.setCurrentIndex(
            self.editor.pad_add_electrode_combo.findData(0)
        )
        self.editor.b_add_pad.setChecked(True)
        self.editor._add_pad_at(10.0, 20.0)

        self.assertTrue(self.editor.is_add_pad_mode)
        self.assertEqual(len(self.editor.pads), 1)
        self.assertFalse(self.editor.items[0]._is_add_target)
        self.assertTrue(self.editor.items[1]._is_add_target)
        self.assertEqual(self.editor.items[1].brush().color(), QColor("#ffd447"))
        pad_item = next(iter(self.editor.pad_items.values()))
        self.assertFalse(pad_item.isSelected())

        self.editor._add_pad_at(30.0, 40.0)
        self.assertFalse(self.editor.is_add_pad_mode)
        self.assertEqual(len(self.editor.pads), 2)
        self.assertFalse(self.editor.items[0]._is_add_target)
        self.assertFalse(self.editor.items[1]._is_add_target)
        last_pad = self.editor.pad_items[max(self.editor.pads)]
        self.assertTrue(last_pad.isSelected())

    def test_escape_leaves_add_mode(self) -> None:
        self.editor.b_add_pad.setChecked(True)
        self.editor._stop_all_add_modes()
        self.assertFalse(self.editor.is_add_pad_mode)
        self.assertEqual(self.editor.b_add_pad.text(), "Add Pad")
        self.assertTrue(self.editor._array_group.isEnabled())


if __name__ == "__main__":
    unittest.main()
