"""Pad frame layout around electrode bodies."""

from __future__ import annotations

import math
import unittest

from mea_editor.electrode import Electrode
from mea_editor.pad_layout import layout_pads_around_electrodes


def _min_center_distance(pads) -> float:
    best = float("inf")
    for i, a in enumerate(pads):
        for b in pads[i + 1 :]:
            best = min(best, math.hypot(a.x - b.x, a.y - b.y))
    return best


class PadLayoutTests(unittest.TestCase):
    def test_pads_clear_large_electrode_bodies(self) -> None:
        electrodes = [
            Electrode(eid=0, x=0.0, y=0.0, radius=50.0, shape="circle"),
            Electrode(eid=1, x=120.0, y=0.0, radius=50.0, shape="circle"),
        ]
        pads = layout_pads_around_electrodes(
            electrodes,
            pad_rows=1,
            pad_spacing=10.0,
            pad_size=8.0,
        )
        self.assertEqual(len(pads), 2)
        electrode_max_x = 120.0 + 50.0
        electrode_min_x = 0.0 - 50.0
        for pad in pads:
            outside_x = pad.x <= electrode_min_x - 8.0 or pad.x >= electrode_max_x + 8.0
            outside_y = abs(pad.y) >= 50.0 + 8.0
            self.assertTrue(
                outside_x or outside_y,
                f"pad at ({pad.x}, {pad.y}) overlaps the electrode bounding box",
            )

    def test_one_pad_per_electrode(self) -> None:
        electrodes = [
            Electrode(eid=i, x=float(i * 40), y=0.0) for i in range(4)
        ]
        pads = layout_pads_around_electrodes(electrodes, pad_rows=1, pad_spacing=20.0)
        self.assertEqual({pad.electrode_eid for pad in pads}, {0, 1, 2, 3})

    def test_spacing_is_center_to_center_along_ring(self) -> None:
        electrodes = [
            Electrode(eid=i, x=float((i % 4) * 5), y=float((i // 4) * 5), radius=1.0)
            for i in range(8)
        ]
        spacing = 50.0
        pads = layout_pads_around_electrodes(
            electrodes,
            pad_rows=1,
            pad_spacing=spacing,
            pad_size=2.0,
        )
        self.assertEqual(len(pads), 8)
        self.assertAlmostEqual(_min_center_distance(pads), spacing, places=6)

    def test_spacing_does_not_depend_on_pad_size(self) -> None:
        electrodes = [
            Electrode(eid=i, x=float((i % 4) * 5), y=float((i // 4) * 5), radius=1.0)
            for i in range(8)
        ]
        small = layout_pads_around_electrodes(
            electrodes, pad_rows=1, pad_spacing=50.0, pad_size=2.0
        )
        large = layout_pads_around_electrodes(
            electrodes, pad_rows=1, pad_spacing=50.0, pad_size=8.0
        )
        small_xy = sorted((round(p.x, 6), round(p.y, 6)) for p in small)
        large_xy = sorted((round(p.x, 6), round(p.y, 6)) for p in large)
        self.assertEqual(small_xy, large_xy)

    def test_spacing_between_pad_rows(self) -> None:
        electrodes = [
            Electrode(eid=i, x=float((i % 8) * 5), y=float((i // 8) * 5), radius=1.0)
            for i in range(64)
        ]
        spacing = 40.0
        pads = layout_pads_around_electrodes(
            electrodes,
            pad_rows=2,
            pad_spacing=spacing,
            pad_size=2.0,
        )
        self.assertEqual(len(pads), 64)
        cx = sum(p.x for p in pads) / len(pads)
        cy = sum(p.y for p in pads) / len(pads)
        radii = sorted(
            {round(max(abs(p.x - cx), abs(p.y - cy)), 6) for p in pads}
        )
        self.assertEqual(len(radii), 2)
        self.assertAlmostEqual(radii[1] - radii[0], spacing, places=6)


if __name__ == "__main__":
    unittest.main()
