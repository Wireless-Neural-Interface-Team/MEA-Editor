"""Map-view label text from the IDs checked in the editor."""

from __future__ import annotations

import unittest

from mea_editor.attribute_schema import AttributeSpec, default_schema
from mea_editor.electrode import (
    BUILTIN_ATTRIBUTE_KEYS,
    DEFAULT_MAP_LABEL_KEYS,
    Electrode,
    electrode_map_view_labels,
)


def _sample() -> Electrode:
    return Electrode(
        eid=1,
        x=0.0,
        y=0.0,
        potentiostat_id=7,
        intan_id="A-003",
        manufacturer_id="M3",
        shank_id="1",
        extra={"site_note": "deep"},
    )


class MapViewLabelsTests(unittest.TestCase):
    def test_default_matches_shank_potentiostat_and_intan(self) -> None:
        electrode = _sample()
        self.assertEqual(electrode.map_view_labels(), ("1-007", "A-003"))
        self.assertEqual(
            electrode.map_view_labels(DEFAULT_MAP_LABEL_KEYS, BUILTIN_ATTRIBUTE_KEYS),
            ("1-007", "A-003"),
        )

    def test_uncheck_shank_leaves_potentiostat_on_contact(self) -> None:
        electrode = _sample()
        self.assertEqual(
            electrode.map_view_labels({"potentiostat_id", "intan_id"}, BUILTIN_ATTRIBUTE_KEYS),
            ("007", "A-003"),
        )

    def test_uncheck_intan_hides_below_label(self) -> None:
        electrode = _sample()
        self.assertEqual(
            electrode.map_view_labels({"potentiostat_id", "shank_id"}, BUILTIN_ATTRIBUTE_KEYS),
            ("1-007", ""),
        )

    def test_uncheck_potentiostat_keeps_shank_on_contact(self) -> None:
        electrode = _sample()
        self.assertEqual(
            electrode.map_view_labels({"intan_id", "shank_id"}, BUILTIN_ATTRIBUTE_KEYS),
            ("1", "A-003"),
        )

    def test_manufacturer_appears_below_when_checked(self) -> None:
        electrode = _sample()
        visible = {"potentiostat_id", "intan_id", "shank_id", "manufacturer_id"}
        self.assertEqual(
            electrode.map_view_labels(visible, BUILTIN_ATTRIBUTE_KEYS),
            ("1-007", "A-003\nM3"),
        )

    def test_extra_attribute_follows_schema_order(self) -> None:
        electrode = _sample()
        schema_keys = [spec.key for spec in default_schema()] + ["site_note"]
        visible = set(DEFAULT_MAP_LABEL_KEYS) | {"site_note"}
        self.assertEqual(
            electrode.map_view_labels(visible, schema_keys),
            ("1-007", "A-003\ndeep"),
        )

    def test_nothing_checked_hides_all_labels(self) -> None:
        electrode = _sample()
        self.assertEqual(electrode.map_view_labels([], BUILTIN_ATTRIBUTE_KEYS), ("", ""))

    def test_empty_intan_shows_placeholder_when_checked(self) -> None:
        values = {"potentiostat_id": 2, "intan_id": "", "shank_id": ""}
        self.assertEqual(
            electrode_map_view_labels(values, {"potentiostat_id", "intan_id"}),
            ("002", "?"),
        )

    def test_schema_labels_cover_electrode_tab_ids(self) -> None:
        labels = [spec.label for spec in default_schema()]
        self.assertEqual(
            labels,
            ["Potentiostat ID", "INTAN ID", "Manufacturer ID", "Shank ID"],
        )
        extra = AttributeSpec(key="site_note", label="Site note")
        self.assertEqual(extra.label, "Site note")


if __name__ == "__main__":
    unittest.main()
