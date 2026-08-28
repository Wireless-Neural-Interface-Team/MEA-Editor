"""Round-trip checks for native save, SpikeInterface export, and XLSX."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mea_editor import __version__
from mea_editor.attribute_schema import AttributeSpec, default_schema
from mea_editor.electrode import Electrode
from mea_editor.electrode_array_editor_io import (
    NATIVE_SPECIFICATION,
    NATIVE_VERSION,
    build_probeinterface_payload,
    export_analysis_xlsx,
    export_array_xlsx,
    export_spikeinterface_json,
    load_array_from_file,
    save_array_to_file,
)
from mea_editor.pad import Pad


def _sample_array() -> tuple[list[Electrode], list[Pad], list[AttributeSpec]]:
    schema = default_schema() + [
        AttributeSpec(key="site_note", label="Site note", value_type="str", default="", unique=False)
    ]
    electrodes = [
        Electrode(
            eid=2,
            x=10.0,
            y=20.0,
            radius=12.0,
            height=8.0,
            potentiostat_id=7,
            intan_id="A-003",
            manufacturer_id="M3",
            shank_id="1",
            shape="rect",
            extra={"site_note": "deep"},
        ),
        Electrode(
            eid=5,
            x=40.0,
            y=20.0,
            radius=6.0,
            potentiostat_id=8,
            intan_id="A-004",
            manufacturer_id="M4",
            shape="square",
            extra={"site_note": "shallow"},
        ),
    ]
    pads = [
        Pad(
            pid=1,
            electrode_eid=2,
            x=-30.0,
            y=20.0,
            radius=10.0,
            height=4.0,
            interface_id="P1",
            system_id="INTAN",
            shape="rect",
        ),
        Pad(
            pid=4,
            electrode_eid=5,
            x=80.0,
            y=20.0,
            radius=10.0,
            interface_id="P2",
            system_id="INTAN",
            shape="square",
        ),
    ]
    return electrodes, pads, schema


class IoRoundTripTests(unittest.TestCase):
    def test_native_save_roundtrip(self) -> None:
        electrodes, pads, schema = _sample_array()
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "array.json")
            save_array_to_file(path, electrodes, "um", pads=pads, electrode_attributes=schema)
            with open(path, encoding="utf-8") as fh:
                payload = json.load(fh)
            self.assertEqual(payload["specification"], NATIVE_SPECIFICATION)
            self.assertEqual(payload["version"], NATIVE_VERSION)
            self.assertEqual(payload["editor_version"], __version__)
            self.assertEqual(len(payload["electrodes"]), 2)
            self.assertEqual(len(payload["pads"]), 2)
            loaded, loaded_pads, units, loaded_schema = load_array_from_file(path)
        self.assertEqual(units, "um")
        self.assertEqual([m.eid for m in loaded], [2, 5])
        self.assertEqual(loaded[0].shape, "rect")
        self.assertEqual(loaded[0].height, 8.0)
        self.assertEqual(loaded[0].intan_id, "A-003")
        self.assertEqual(loaded[0].manufacturer_id, "M3")
        self.assertEqual(loaded[0].extra.get("site_note"), "deep")
        extra_keys = {spec.key for spec in loaded_schema if not spec.builtin}
        self.assertIn("site_note", extra_keys)
        self.assertEqual([p.pid for p in loaded_pads], [1, 4])
        self.assertEqual(loaded_pads[0].electrode_eid, 2)
        self.assertEqual(loaded_pads[0].interface_id, "P1")
        self.assertEqual(loaded_pads[0].shape, "rect")
        self.assertEqual(loaded_pads[0].height, 4.0)

    def test_spikeinterface_export_roundtrip_restores_native_ids(self) -> None:
        electrodes, pads, schema = _sample_array()
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "probe.json")
            export_spikeinterface_json(
                path,
                electrodes,
                "um",
                pads=pads,
                electrode_attributes=schema,
            )
            payload = build_probeinterface_payload(
                electrodes,
                "um",
                pads=pads,
                electrode_attributes=schema,
            )
            probe = payload["probes"][0]
            self.assertEqual(probe["device_channel_indices"], [3, 4])
            self.assertEqual(probe["contact_ids"], ["M3", "M4"])
            self.assertEqual(probe["contact_shapes"], ["rect", "square"])
            self.assertEqual(probe["contact_shape_params"][0]["width"], 24.0)
            self.assertEqual(probe["contact_shape_params"][0]["height"], 16.0)
            self.assertEqual(probe["contact_annotations"]["intan_id"], ["A-003", "A-004"])
            self.assertEqual(probe["contact_annotations"]["site_note"], ["deep", "shallow"])
            self.assertEqual(probe["contact_annotations"]["pad_interface_id"], ["P1", "P2"])
            loaded, loaded_pads, units, loaded_schema = load_array_from_file(path)
        self.assertEqual(units, "um")
        self.assertEqual(loaded_pads, [])
        self.assertEqual(loaded[0].intan_id, "A-003")
        self.assertEqual(loaded[0].manufacturer_id, "M3")
        self.assertEqual(loaded[0].potentiostat_id, 7)
        self.assertEqual(loaded[0].eid, 2)
        self.assertEqual(loaded[0].shape, "rect")
        self.assertEqual(loaded[0].extra.get("site_note"), "deep")
        extra_keys = {spec.key for spec in loaded_schema if not spec.builtin}
        self.assertIn("site_note", extra_keys)

    def test_legacy_probeinterface_without_native_annotations(self) -> None:
        payload = {
            "specification": "probeinterface",
            "version": "0.3.1",
            "probes": [
                {
                    "ndim": 2,
                    "si_units": "um",
                    "annotations": {},
                    "contact_annotations": {},
                    "contact_positions": [[1.0, 2.0]],
                    "contact_plane_axes": [[[1.0, 0.0], [0.0, 1.0]]],
                    "contact_shapes": ["circle"],
                    "contact_shape_params": [{"radius": 12.0}],
                    "device_channel_indices": [3],
                    "contact_ids": ["A-003"],
                    "shank_ids": [""],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "legacy.json")
            Path(path).write_text(json.dumps(payload), encoding="utf-8")
            loaded, pads, units, _schema = load_array_from_file(path)
        self.assertEqual(units, "um")
        self.assertEqual(pads, [])
        self.assertEqual(loaded[0].potentiostat_id, 3)
        self.assertEqual(loaded[0].intan_id, "A-003")
        self.assertEqual(loaded[0].manufacturer_id, "")

    def test_xlsx_exports_include_pads_and_extras(self) -> None:
        electrodes, pads, schema = _sample_array()
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            analysis_path = str(Path(tmp) / "analysis.xlsx")
            array_path = str(Path(tmp) / "array.xlsx")
            export_analysis_xlsx(analysis_path, electrodes, pads=pads, electrode_attributes=schema)
            export_array_xlsx(
                array_path,
                electrodes,
                pads=pads,
                electrode_attributes=schema,
                si_units="um",
            )
            from openpyxl import load_workbook

            analysis = load_workbook(analysis_path)
            try:
                analysis_sheet = analysis.active
                self.assertEqual(
                    [cell.value for cell in analysis_sheet[1]],
                    [
                        "channel",
                        "row",
                        "col",
                        "shape",
                        "intan_id",
                        "manufacturer_id",
                        "shank_id",
                        "enabled",
                        "site_note",
                        "pad_interface_id",
                        "pad_system_id",
                    ],
                )
                self.assertEqual(analysis_sheet["A2"].value, 7)
                self.assertEqual(analysis_sheet["D2"].value, "rect")
                self.assertEqual(analysis_sheet["J2"].value, "P1")
            finally:
                analysis.close()

            workbook = load_workbook(array_path)
            try:
                self.assertEqual(workbook.sheetnames, ["array", "pads", "electrode_attributes"])
                self.assertEqual(workbook["pads"]["A2"].value, 1)
                self.assertEqual(workbook["pads"]["M2"].value, "P1")
                self.assertEqual(workbook["array"]["I2"].value, "rect")
                self.assertEqual(workbook["array"]["N2"].value, "P1")
            finally:
                workbook.close()


class VersionTests(unittest.TestCase):
    def test_package_version_is_semver(self) -> None:
        parts = __version__.split(".")
        self.assertGreaterEqual(len(parts), 2)
        self.assertTrue(all(part.isdigit() for part in parts))

    def test_version_module_matches_package(self) -> None:
        from mea_editor._version import __version__ as raw

        self.assertEqual(raw, __version__)


if __name__ == "__main__":
    unittest.main()
