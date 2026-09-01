"""Creation defaults in the Actions group are used when adding items."""

from __future__ import annotations

import unittest

from PySide6.QtWidgets import QApplication, QComboBox, QLineEdit

from mea_editor.contact_shape import DEFAULT_PAD_SHAPE, size_field_from_stored_half
from mea_editor.electrode import (
    DEFAULT_LABEL_ORIENTATION,
    DEFAULT_LABEL_POSITION,
    DEFAULT_RADIUS,
    DEFAULT_SHAPE,
    Electrode,
)
from mea_editor.electrode_array_editor_qt import ElectrodeArrayEditorQt
from mea_editor.orientation_marker import DEFAULT_MARKER_RADIUS, DEFAULT_MARKER_SHAPE
from mea_editor.pad import DEFAULT_PAD_RADIUS


class GeometryFromAddFieldsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def test_parses_rect_sizes_and_falls_back_on_invalid_text(self) -> None:
        shape = QComboBox()
        shape.addItems(["circle", "square", "rect"])
        shape.setCurrentText("rect")
        size = QLineEdit("30")
        height = QLineEdit("10")
        parsed_shape, radius, stored_h = ElectrodeArrayEditorQt._geometry_from_add_fields(
            shape, size, height, DEFAULT_SHAPE, DEFAULT_RADIUS
        )
        self.assertEqual(parsed_shape, "rect")
        self.assertAlmostEqual(radius, 15.0)
        self.assertAlmostEqual(stored_h, 5.0)

        size.setText("nope")
        height.setText("")
        parsed_shape, radius, stored_h = ElectrodeArrayEditorQt._geometry_from_add_fields(
            shape, size, height, DEFAULT_SHAPE, DEFAULT_RADIUS
        )
        self.assertEqual(parsed_shape, "rect")
        self.assertAlmostEqual(radius, DEFAULT_RADIUS)
        self.assertAlmostEqual(stored_h, DEFAULT_RADIUS)


class AddDefaultsEditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.editor = ElectrodeArrayEditorQt()

    def tearDown(self) -> None:
        self.editor.is_dirty = False
        self.editor.close()

    def test_default_action_widgets_match_model_defaults(self) -> None:
        self.assertEqual(self.editor.add_electrode_shape_combo.currentText(), DEFAULT_SHAPE)
        self.assertEqual(
            self.editor.add_electrode_size_edit.text(),
            f"{size_field_from_stored_half(DEFAULT_SHAPE, DEFAULT_RADIUS):.2f}",
        )
        self.assertEqual(self.editor.add_pad_shape_combo.currentText(), DEFAULT_PAD_SHAPE)
        self.assertEqual(
            self.editor.add_pad_size_edit.text(),
            f"{size_field_from_stored_half(DEFAULT_PAD_SHAPE, DEFAULT_PAD_RADIUS):.2f}",
        )
        self.assertEqual(self.editor.add_marker_shape_combo.currentText(), DEFAULT_MARKER_SHAPE)
        self.assertEqual(
            self.editor.add_marker_size_edit.text(),
            f"{size_field_from_stored_half(DEFAULT_MARKER_SHAPE, DEFAULT_MARKER_RADIUS):.2f}",
        )
        self.assertTrue(self.editor.add_electrode_height_edit.isHidden())
        self.assertFalse(hasattr(self.editor, "add_marker_label_position_combo"))

    def test_add_electrode_uses_action_defaults_not_selection_form(self) -> None:
        self.editor.shape_combo.setCurrentText("square")
        self.editor.radius_edit.setText("99")
        self.editor._set_label_position_combo(self.editor.label_position_combo, "above", mixed=False)
        self.editor._set_label_orientation_combo(self.editor.label_orientation_combo, 180, mixed=False)

        self.editor.add_electrode_shape_combo.setCurrentText("rect")
        self.editor.add_electrode_size_edit.setText("30")
        self.editor.add_electrode_height_edit.setText("10")
        self.editor._set_label_position_combo(
            self.editor.add_electrode_label_position_combo, "left", mixed=False
        )
        self.editor._set_label_orientation_combo(
            self.editor.add_electrode_label_orientation_combo, 90, mixed=False
        )

        self.editor._add_electrode_at(1.0, 2.0)
        electrode = next(iter(self.editor.electrodes.values()))
        self.assertEqual(electrode.shape, "rect")
        self.assertAlmostEqual(electrode.radius, 15.0)
        self.assertAlmostEqual(electrode.height, 5.0)
        self.assertEqual(electrode.label_position, "left")
        self.assertEqual(electrode.label_orientation, 90)
        self.assertEqual(self.editor.pads, {})

    def test_add_pad_uses_action_defaults(self) -> None:
        self.editor._set_array([Electrode(eid=0, x=0.0, y=0.0)], pads=[])
        self.editor.add_pad_shape_combo.setCurrentText("square")
        self.editor.add_pad_size_edit.setText("24")
        self.editor._set_label_position_combo(
            self.editor.add_pad_label_position_combo, "above", mixed=False
        )
        self.editor._set_label_orientation_combo(
            self.editor.add_pad_label_orientation_combo, 180, mixed=False
        )
        self.editor._add_pad_at(40.0, 50.0)
        pad = next(iter(self.editor.pads.values()))
        self.assertEqual(pad.shape, "square")
        self.assertAlmostEqual(pad.radius, 12.0)
        self.assertEqual(pad.height, 0.0)
        self.assertEqual(pad.label_position, "above")
        self.assertEqual(pad.label_orientation, 180)
        self.assertAlmostEqual(pad.x, 40.0)
        self.assertAlmostEqual(pad.y, 50.0)

    def test_add_marker_uses_action_defaults_not_properties(self) -> None:
        self.editor.marker_shape_combo.setCurrentText("circle")
        self.editor.marker_radius_edit.setText("99")
        self.editor.add_marker_shape_combo.setCurrentText("rect")
        self.editor.add_marker_size_edit.setText("16")
        self.editor.add_marker_height_edit.setText("6")
        self.editor._add_marker_at(3.0, 4.0)
        marker = next(iter(self.editor.orientation_markers.values()))
        self.assertEqual(marker.shape, "rect")
        self.assertAlmostEqual(marker.radius, 8.0)
        self.assertAlmostEqual(marker.height, 3.0)
        self.assertEqual(marker.label_position, DEFAULT_LABEL_POSITION)
        self.assertEqual(marker.label_orientation, DEFAULT_LABEL_ORIENTATION)

    def test_changing_add_shape_shows_height_for_rect(self) -> None:
        self.assertTrue(self.editor.add_electrode_height_edit.isHidden())
        self.editor.add_electrode_shape_combo.setCurrentText("rect")
        self.assertFalse(self.editor.add_electrode_height_edit.isHidden())
        self.assertEqual(self.editor.add_electrode_size_label.text(), "Width")


if __name__ == "__main__":
    unittest.main()
