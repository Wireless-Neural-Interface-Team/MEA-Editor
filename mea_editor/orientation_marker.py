"""
Shared data structures for orientation markers.

An orientation marker is a fabrication / layout fiducial: a white square used
to read the orientation of the array. It is not an electrode or a pad, is not
linked to either, and is not a SpikeInterface contact.

It is persisted in native JSON and written to the Excel / analysis workbooks
(geometry only). SpikeInterface export omits it. Map-label side and rotation
are native JSON only.
"""

from __future__ import annotations

from dataclasses import dataclass

from .electrode import DEFAULT_LABEL_ORIENTATION, DEFAULT_LABEL_POSITION

DEFAULT_MARKER_SIDE = 20.0


@dataclass(frozen=True, slots=True)
class OrientationMarkerSnapshot:
    """Immutable copy of editable orientation-marker fields for undo/redo."""

    x: float
    y: float
    side: float
    label_position: str
    label_orientation: int


@dataclass(slots=True)
class OrientationMarker:
    """
    In-memory data model for one orientation marker.

    Field groups:
    - identity: marker_id (editor-assigned, like electrode eid / pad_id)
    - geometry: x, y, side (full square side length)
    - editor display: label_position (above / below / left / right) and
      label_orientation (0 / 90 / 180 / 270 degrees)

    Notes:
    - shape is always a square; there is no SpikeInterface contact shape.
    - side is the full extent (not a stored half-width).
    - There is no electrode or pad association.
    - The marker ID is drawn next to the square. label_position and
      label_orientation are editor display only (native JSON); they are
      omitted from SpikeInterface and XLSX.
    """

    marker_id: int
    x: float
    y: float
    side: float = DEFAULT_MARKER_SIDE
    label_position: str = DEFAULT_LABEL_POSITION
    label_orientation: int = DEFAULT_LABEL_ORIENTATION

    def snapshot(self) -> OrientationMarkerSnapshot:
        """Return an immutable copy of editable fields."""
        return OrientationMarkerSnapshot(
            x=self.x,
            y=self.y,
            side=self.side,
            label_position=self.label_position,
            label_orientation=self.label_orientation,
        )

    def restore(self, snap: OrientationMarkerSnapshot) -> None:
        """Apply a snapshot onto this model (keeps marker_id)."""
        self.x = snap.x
        self.y = snap.y
        self.side = snap.side
        self.label_position = snap.label_position
        self.label_orientation = snap.label_orientation

    @classmethod
    def from_snapshot(cls, marker_id: int, snap: OrientationMarkerSnapshot) -> OrientationMarker:
        """Build a new marker from a snapshot."""
        return cls(
            marker_id=marker_id,
            x=snap.x,
            y=snap.y,
            side=snap.side,
            label_position=snap.label_position,
            label_orientation=snap.label_orientation,
        )

    def half_side(self) -> float:
        """Half-extent used for drawing and bounds."""
        return self.side / 2.0
