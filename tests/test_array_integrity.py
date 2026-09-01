"""Identifier uniqueness, pairing flags, and colliding ids."""

from __future__ import annotations

import unittest

from mea_editor.array_integrity import (
    ensure_unique_marker_ids,
    ensure_unique_model_ids,
    pairing_problems,
    refresh_status_flags,
)
from mea_editor.attribute_schema import AttributeSpec, default_schema
from mea_editor.electrode import Electrode
from mea_editor.orientation_marker import OrientationMarker
from mea_editor.pad import Pad


class UniqueIdTests(unittest.TestCase):
    def test_duplicate_eid_keeps_first_and_leaves_pad_link(self) -> None:
        electrodes = [
            Electrode(eid=0, x=0.0, y=0.0),
            Electrode(eid=0, x=10.0, y=0.0),
        ]
        pads = [Pad(pad_id=0, electrode_eid=0, x=-20.0, y=0.0)]
        eid_fixes, pad_fixes = ensure_unique_model_ids(electrodes, pads)
        self.assertEqual(eid_fixes, 1)
        self.assertEqual(pad_fixes, 0)
        self.assertEqual(electrodes[0].eid, 0)
        self.assertEqual(electrodes[1].eid, 1)
        self.assertEqual(pads[0].electrode_eid, 0)


class UniqueMarkerIdTests(unittest.TestCase):
    def test_duplicate_marker_id_keeps_first(self) -> None:
        markers = [
            OrientationMarker(marker_id=0, x=0.0, y=0.0, radius=10.0),
            OrientationMarker(marker_id=0, x=10.0, y=0.0, radius=6.0),
        ]
        changes = ensure_unique_marker_ids(markers)
        self.assertEqual(changes, 1)
        self.assertEqual(markers[0].marker_id, 0)
        self.assertEqual(markers[1].marker_id, 1)
        self.assertEqual(markers[1].radius, 6.0)


class StatusFlagTests(unittest.TestCase):
    def test_intan_channel_collisions_and_invalid(self) -> None:
        electrodes = [
            Electrode(eid=0, x=0.0, y=0.0, intan_id="A-003"),
            Electrode(eid=1, x=1.0, y=0.0, intan_id="A003"),
            Electrode(eid=2, x=2.0, y=0.0, intan_id="A-032"),
            Electrode(eid=3, x=3.0, y=0.0, intan_id=""),
        ]
        refresh_status_flags(electrodes, [], default_schema())
        self.assertTrue(electrodes[0].has_intan_duplicate)
        self.assertTrue(electrodes[1].has_intan_duplicate)
        self.assertTrue(electrodes[2].has_intan_duplicate)
        self.assertTrue(electrodes[3].has_intan_duplicate)

    def test_manufacturer_partial_fill(self) -> None:
        electrodes = [
            Electrode(eid=0, x=0.0, y=0.0, manufacturer_id="M1", intan_id="A-000"),
            Electrode(eid=1, x=1.0, y=0.0, manufacturer_id="", intan_id="A-001"),
        ]
        refresh_status_flags(electrodes, [], default_schema())
        self.assertFalse(electrodes[0].has_manufacturer_duplicate)
        self.assertTrue(electrodes[1].has_manufacturer_duplicate)

    def test_extra_unique_per_shank(self) -> None:
        schema = default_schema() + [
            AttributeSpec(key="site_note", label="Site note", unique=True, unique_scope="per_shank")
        ]
        electrodes = [
            Electrode(eid=0, x=0.0, y=0.0, shank_id="1", extra={"site_note": "a"}, intan_id="A-000"),
            Electrode(eid=1, x=1.0, y=0.0, shank_id="1", extra={"site_note": "a"}, intan_id="A-001"),
            Electrode(eid=2, x=2.0, y=0.0, shank_id="2", extra={"site_note": "a"}, intan_id="A-002"),
        ]
        refresh_status_flags(electrodes, [], schema)
        self.assertTrue(electrodes[0].has_extra_duplicate)
        self.assertTrue(electrodes[1].has_extra_duplicate)
        self.assertFalse(electrodes[2].has_extra_duplicate)

    def test_missing_pad_pairing(self) -> None:
        electrodes = [
            Electrode(eid=0, x=0.0, y=0.0, intan_id="A-000"),
            Electrode(eid=1, x=1.0, y=0.0, intan_id="A-001"),
        ]
        pads = [Pad(pad_id=0, electrode_eid=0, x=-10.0, y=0.0)]
        refresh_status_flags(electrodes, pads, default_schema())
        self.assertFalse(electrodes[0].has_missing_pad)
        self.assertTrue(electrodes[1].has_missing_pad)
        problems = pairing_problems(electrodes, pads)
        self.assertTrue(any("no pad" in item for item in problems))


if __name__ == "__main__":
    unittest.main()
