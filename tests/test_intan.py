"""INTAN ID conversion and SpikeInterface channel uniqueness."""

from __future__ import annotations

import unittest

from mea_editor.electrode_array_editor_io import (
    format_intan_id,
    intan_id_to_channel_id,
    try_intan_channel_id,
)


class IntanIdTests(unittest.TestCase):
    def test_format_and_parse_roundtrip(self) -> None:
        self.assertEqual(format_intan_id(0), "A-000")
        self.assertEqual(format_intan_id(31), "A-031")
        self.assertEqual(format_intan_id(32), "B-000")
        self.assertEqual(intan_id_to_channel_id("A-003"), 3)
        self.assertEqual(intan_id_to_channel_id("D-018"), 114)
        self.assertEqual(intan_id_to_channel_id("NC"), -1)

    def test_equivalent_spellings_share_channel(self) -> None:
        self.assertEqual(intan_id_to_channel_id("A-003"), 3)
        self.assertEqual(intan_id_to_channel_id("A003"), 3)
        self.assertEqual(intan_id_to_channel_id("a-003"), 3)
        self.assertEqual(intan_id_to_channel_id("3"), 3)

    def test_port_channel_out_of_range(self) -> None:
        with self.assertRaises(ValueError):
            intan_id_to_channel_id("A-032")
        self.assertIsNone(try_intan_channel_id("A-032"))
        self.assertEqual(intan_id_to_channel_id("B-000"), 32)

    def test_empty_and_invalid(self) -> None:
        with self.assertRaises(ValueError):
            intan_id_to_channel_id("")
        with self.assertRaises(ValueError):
            intan_id_to_channel_id("not-an-id")
        self.assertIsNone(try_intan_channel_id(""))
        self.assertIsNone(try_intan_channel_id("xyz"))


if __name__ == "__main__":
    unittest.main()
