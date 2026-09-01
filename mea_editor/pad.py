"""
Shared data structures for connector pads.

Pads are not electrodes: they are interfaces toward other electronic
systems. Each pad is associated with one electrode (`electrode_eid`).
Each electrode should have exactly one pad; the editor highlights
unpaired or shared links and asks before saving.

The only pad identifier is `pad_id`, assigned by the editor like electrode `eid`.
Users cannot define a separate pad ID.
"""

from __future__ import annotations

from dataclasses import dataclass

from .contact_shape import (
    CONTACT_SHAPES,
    DEFAULT_PAD_SHAPE,
    primary_size_field_label,
    size_field_from_stored_half,
    stored_half_from_size_field,
)
from .electrode import DEFAULT_LABEL_ORIENTATION, DEFAULT_LABEL_POSITION


DEFAULT_PAD_RADIUS = 10.0
PAD_SHAPES = CONTACT_SHAPES

pad_size_field_label = primary_size_field_label
stored_radius_from_size_field = stored_half_from_size_field
size_field_from_stored_radius = size_field_from_stored_half


@dataclass(frozen=True, slots=True)
class PadSnapshot:
    """Immutable copy of editable pad fields for undo/redo."""

    electrode_eid: int
    x: float
    y: float
    radius: float
    height: float
    shape: str
    label_position: str
    label_orientation: int


@dataclass(slots=True)
class Pad:
    """
    In-memory data model for one connector pad.

    Field groups:
    - identity: pad_id (editor-assigned, like electrode eid)
    - association: electrode_eid (required link to an electrode)
    - geometry: x, y, radius, height
    - editor display: label_position (above / below / left / right) and
      label_orientation (0 / 90 / 180 / 270 degrees)
    - editor state: pairing flags

    Notes:
    - shape is a SpikeInterface contact shape: circle, square, or rect.
    - radius is the stored half-extent along X (true radius for a circle).
    - height is the stored half-extent along Y for rect; 0 means use radius.
    - Pairing flags are computed by the editor and drive display color.
    - label_position and label_orientation are editor display only (native
      JSON); they are omitted from SpikeInterface and XLSX exports.
    """

    pad_id: int
    electrode_eid: int
    x: float
    y: float
    radius: float = DEFAULT_PAD_RADIUS
    height: float = 0.0
    shape: str = DEFAULT_PAD_SHAPE
    label_position: str = DEFAULT_LABEL_POSITION
    label_orientation: int = DEFAULT_LABEL_ORIENTATION
    has_shared_electrode: bool = False
    has_missing_electrode: bool = False

    def snapshot(self) -> PadSnapshot:
        """Return an immutable copy of editable fields."""
        return PadSnapshot(
            electrode_eid=self.electrode_eid,
            x=self.x,
            y=self.y,
            radius=self.radius,
            height=self.height,
            shape=self.shape,
            label_position=self.label_position,
            label_orientation=self.label_orientation,
        )

    def restore(self, snap: PadSnapshot) -> None:
        """Apply a snapshot onto this model (keeps pad_id and pairing flags)."""
        self.electrode_eid = snap.electrode_eid
        self.x = snap.x
        self.y = snap.y
        self.radius = snap.radius
        self.height = snap.height
        self.shape = snap.shape
        self.label_position = snap.label_position
        self.label_orientation = snap.label_orientation

    @classmethod
    def from_snapshot(cls, pad_id: int, snap: PadSnapshot) -> Pad:
        """Build a new pad from a snapshot."""
        return cls(
            pad_id=pad_id,
            electrode_eid=snap.electrode_eid,
            x=snap.x,
            y=snap.y,
            radius=snap.radius,
            height=snap.height,
            shape=snap.shape,
            label_position=snap.label_position,
            label_orientation=snap.label_orientation,
        )

    def has_any_duplicate(self) -> bool:
        """True if a pairing condition should highlight this pad."""
        return self.has_shared_electrode or self.has_missing_electrode
