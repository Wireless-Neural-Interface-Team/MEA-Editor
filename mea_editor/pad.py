"""
Shared data structures for connector pads.

Pads are not electrodes: they are interfaces toward other electronic
systems. Each pad is associated with exactly one electrode (`electrode_eid`),
and each electrode must have exactly one pad.
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


DEFAULT_PAD_RADIUS = 10.0
DEFAULT_INTERFACE_ID = ""
DEFAULT_SYSTEM_ID = ""
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
    enabled: bool
    interface_id: str
    system_id: str
    shape: str


@dataclass(slots=True)
class Pad:
    """
    In-memory data model for one connector pad.

    Field groups:
    - association: electrode_eid (required link to an electrode)
    - geometry: x, y, radius, height
    - interface: interface_id, system_id
    - editor state: duplicate / pairing flags, enabled

    Notes:
    - shape is a SpikeInterface contact shape: circle, square, or rect.
    - radius is the stored half-extent along X (true radius for a circle).
    - height is the stored half-extent along Y for rect; 0 means use radius.
    - Duplicate and pairing flags are computed by the editor and drive display color.
    """

    pid: int
    electrode_eid: int
    x: float
    y: float
    radius: float = DEFAULT_PAD_RADIUS
    height: float = 0.0
    enabled: bool = True
    interface_id: str = DEFAULT_INTERFACE_ID
    system_id: str = DEFAULT_SYSTEM_ID
    shape: str = DEFAULT_PAD_SHAPE
    has_interface_duplicate: bool = False
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
            enabled=self.enabled,
            interface_id=self.interface_id,
            system_id=self.system_id,
            shape=self.shape,
        )

    def restore(self, snap: PadSnapshot) -> None:
        """Apply a snapshot onto this model (keeps pid and duplicate flags)."""
        self.electrode_eid = snap.electrode_eid
        self.x = snap.x
        self.y = snap.y
        self.radius = snap.radius
        self.height = snap.height
        self.enabled = snap.enabled
        self.interface_id = snap.interface_id
        self.system_id = snap.system_id
        self.shape = snap.shape

    @classmethod
    def from_snapshot(cls, pid: int, snap: PadSnapshot) -> Pad:
        """Build a new pad from a snapshot."""
        return cls(
            pid=pid,
            electrode_eid=snap.electrode_eid,
            x=snap.x,
            y=snap.y,
            radius=snap.radius,
            height=snap.height,
            enabled=snap.enabled,
            interface_id=snap.interface_id,
            system_id=snap.system_id,
            shape=snap.shape,
        )

    def has_any_duplicate(self) -> bool:
        """True if a pairing or identifier condition should highlight this pad."""
        return (
            self.has_interface_duplicate
            or self.has_shared_electrode
            or self.has_missing_electrode
        )
