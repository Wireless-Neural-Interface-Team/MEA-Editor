"""Filter and row-building checks for the electrode table window."""

from __future__ import annotations

import unittest

from mea_editor.attribute_schema import AttributeSpec, default_schema
from mea_editor.electrode import Electrode
from mea_editor.electrode_table_window import (
    ALL_FILTER,
    EMPTY_FILTER,
    ElectrodeTableWindow,
    electrode_row,
    format_cell,
    pads_by_electrode,
    row_matches,
    table_columns,
    unique_attribute_values,
)
from mea_editor.pad import Pad


def _sample() -> tuple[list[Electrode], list[Pad], list[AttributeSpec]]:
    schema = default_schema() + [
        AttributeSpec(key="site_note", label="Site note", value_type="str", default="")
    ]
    electrodes = [
        Electrode(
            eid=2,
            x=10.0,
            y=20.0,
            potentiostat_id=7,
            intan_id="A-003",
            manufacturer_id="M3",
            shank_id="1",
            extra={"site_note": "deep"},
        ),
        Electrode(
            eid=5,
            x=40.0,
            y=20.0,
            potentiostat_id=8,
            intan_id="A-004",
            manufacturer_id="",
            shank_id="2",
            extra={"site_note": ""},
        ),
    ]
    pads = [
        Pad(pid=1, electrode_eid=2, x=100.0, y=20.0, interface_id="PIN-01", system_id="INTAN"),
    ]
    return electrodes, pads, schema


class ElectrodeTableHelpersTests(unittest.TestCase):
    def test_columns_include_schema_and_pad_fields(self) -> None:
        _electrodes, _pads, schema = _sample()
        keys = [key for key, _label in table_columns(schema)]
        self.assertIn("eid", keys)
        self.assertIn("intan_id", keys)
        self.assertIn("site_note", keys)
        self.assertIn("pad_interface_id", keys)
        self.assertLess(keys.index("intan_id"), keys.index("site_note"))
        self.assertLess(keys.index("site_note"), keys.index("pad_interface_id"))

    def test_row_includes_attribute_and_linked_pad(self) -> None:
        electrodes, pads, schema = _sample()
        pad_map = pads_by_electrode(pads)
        row = electrode_row(electrodes[0], pad_map.get(2), schema)
        self.assertEqual(row["eid"], 2)
        self.assertEqual(row["intan_id"], "A-003")
        self.assertEqual(row["site_note"], "deep")
        self.assertEqual(row["pad_interface_id"], "PIN-01")
        self.assertEqual(row["pad_pid"], 1)

        empty_pad_row = electrode_row(electrodes[1], pad_map.get(5), schema)
        self.assertEqual(empty_pad_row["pad_interface_id"], "")
        self.assertEqual(empty_pad_row["pad_pid"], None)

    def test_search_matches_any_column(self) -> None:
        electrodes, pads, schema = _sample()
        row = electrode_row(electrodes[0], pads[0], schema)
        display = [format_cell(value) for value in row.values()]
        attribute_display = {spec.key: format_cell(row[spec.key]) for spec in schema}
        self.assertTrue(row_matches(display, "A-003", {}, attribute_display))
        self.assertTrue(row_matches(display, "pin-01", {}, attribute_display))
        self.assertFalse(row_matches(display, "missing", {}, attribute_display))

    def test_attribute_filter_exact_and_empty(self) -> None:
        electrodes, pads, schema = _sample()
        row = electrode_row(electrodes[1], None, schema)
        display = [format_cell(value) for value in row.values()]
        attribute_display = {spec.key: format_cell(row[spec.key]) for spec in schema}
        self.assertTrue(
            row_matches(display, "", {"shank_id": "2"}, attribute_display)
        )
        self.assertFalse(
            row_matches(display, "", {"shank_id": "1"}, attribute_display)
        )
        self.assertTrue(
            row_matches(display, "", {"manufacturer_id": EMPTY_FILTER}, attribute_display)
        )
        self.assertTrue(
            row_matches(display, "", {"shank_id": ALL_FILTER}, attribute_display)
        )

    def test_unique_values_include_empty_token(self) -> None:
        electrodes, _pads, schema = _sample()
        rows = [electrode_row(model, None, schema) for model in electrodes]
        values = unique_attribute_values(rows, "manufacturer_id")
        self.assertIn(EMPTY_FILTER, values)
        self.assertIn("M3", values)


class ElectrodeTableWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from PySide6.QtWidgets import QApplication

        cls._app = QApplication.instance() or QApplication([])

    def test_reload_search_filter_and_selection_signal(self) -> None:
        electrodes, pads, schema = _sample()
        window = ElectrodeTableWindow()
        chosen: list[list[int]] = []
        window.electrodes_chosen.connect(chosen.append)
        window.reload(electrodes, pads, schema)
        self.assertEqual(window.model.rowCount(), 2)
        self.assertEqual(window.proxy.rowCount(), 2)
        self.assertIn("intan_id", window._filter_combos)

        window.search_edit.setText("A-003")
        self.assertEqual(window.proxy.rowCount(), 1)

        window.search_edit.clear()
        window._filter_combos["shank_id"].setCurrentText("2")
        self.assertEqual(window.proxy.rowCount(), 1)

        window._clear_filters()
        self.assertEqual(window.proxy.rowCount(), 2)

        window.table.selectRow(0)
        self.assertTrue(chosen)
        self.assertEqual(len(chosen[-1]), 1)
        window.close()


if __name__ == "__main__":
    unittest.main()
