"""
Shared data structures for the electrode array editor.

This module intentionally stays minimal:
- one dataclass (`Electrode`) used by both GUI and I/O layers,
- a frozen snapshot type for undo/redo,
- no Qt dependency,
- no file-format dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .contact_shape import CONTACT_SHAPES, DEFAULT_ELECTRODE_SHAPE


DEFAULT_RADIUS = 12.0
DEFAULT_INTAN_ID = "A-000"
DEFAULT_MANUFACTURER_ID = ""
DEFAULT_SHAPE = DEFAULT_ELECTRODE_SHAPE
ELECTRODE_SHAPES = CONTACT_SHAPES
DEFAULT_PLANE_AXIS = (1.0, 0.0, 0.0, 1.0)
BUILTIN_ATTRIBUTE_KEYS = ("potentiostat_id", "intan_id", "manufacturer_id", "shank_id")
DEFAULT_MAP_LABEL_KEYS = ("potentiostat_id", "intan_id", "shank_id")
_CENTER_MAP_LABEL_KEYS = frozenset({"potentiostat_id", "shank_id"})

AttrValue = str | int | float


def electrode_center_label(potentiostat_id: int, shank_id: str) -> str:
    """
    Compact identity used outside map views (combo boxes, etc.).

    Format:
    - with shank: "<shank>-<potentiostat 3 digits>" (example: "1-002")
    - without shank: "<potentiostat 3 digits>"
    """
    potentiostat = f"{int(potentiostat_id):03d}"
    shank = str(shank_id).strip()
    return f"{shank}-{potentiostat}" if shank else potentiostat


def format_map_label_value(key: str, value: AttrValue) -> str:
    """Format one electrode attribute for a map-view label."""
    if key == "potentiostat_id":
        try:
            return f"{int(value):03d}"
        except (TypeError, ValueError):
            return str(value).strip()
    return str(value).strip()


def electrode_map_view_labels(
    values: dict[str, AttrValue],
    visible_keys: Iterable[str] | None = None,
    schema_keys: Iterable[str] | None = None,
) -> tuple[str, str]:
    """
    Labels drawn on electrode and pad map items.

    Returns (center_text, below_text):
    - center: shank and/or potentiostat when those IDs are visible
    - below: other visible IDs in schema order (INTAN, manufacturer, extras)
    """
    visible = set(DEFAULT_MAP_LABEL_KEYS if visible_keys is None else visible_keys)
    order = list(BUILTIN_ATTRIBUTE_KEYS if schema_keys is None else schema_keys)
    for key in visible:
        if key not in order:
            order.append(key)

    center_parts: list[str] = []
    if "shank_id" in visible:
        shank = format_map_label_value("shank_id", values.get("shank_id", ""))
        if shank:
            center_parts.append(shank)
    if "potentiostat_id" in visible:
        center_parts.append(
            format_map_label_value("potentiostat_id", values.get("potentiostat_id", 0))
        )
    center = "-".join(center_parts)

    below_parts: list[str] = []
    for key in order:
        if key not in visible or key in _CENTER_MAP_LABEL_KEYS:
            continue
        text = format_map_label_value(key, values.get(key, ""))
        if not text and key == "intan_id":
            text = "?"
        if text:
            below_parts.append(text)
    return center, "\n".join(below_parts)


@dataclass(frozen=True, slots=True)
class ElectrodeSnapshot:
    """Immutable copy of editable electrode fields for undo/redo."""

    x: float
    y: float
    radius: float
    height: float
    potentiostat_id: int
    intan_id: str
    manufacturer_id: str
    contact_plane_axis: tuple[float, float, float, float]
    shank_id: str
    shape: str
    extra: dict[str, AttrValue]


@dataclass(slots=True)
class Electrode:
    """
    In-memory data model for one electrode/contact.

    Field groups:
    - geometry: x, y, radius, height
    - identification: potentiostat_id, intan_id, manufacturer_id, shank_id
    - extra attributes: file-defined key/value map (`extra`)
    - orientation metadata: contact_plane_axis (x0, x1, y0, y1)
    - editor state: duplicate flags

    Notes:
    - shape is a SpikeInterface contact shape: circle, square, or rect.
    - radius is the stored half-extent along X (true radius for a circle).
    - height is the stored half-extent along Y for rect; 0 means use radius.
    - Duplicate flags are computed by the editor and drive display color.
    - Built-in identifiers are always present; extra attributes live in `extra`
      and follow the file-level schema.
    """

    eid: int
    x: float
    y: float
    radius: float = DEFAULT_RADIUS
    height: float = 0.0
    potentiostat_id: int = 0
    intan_id: str = DEFAULT_INTAN_ID
    manufacturer_id: str = DEFAULT_MANUFACTURER_ID
    contact_plane_axis: tuple[float, float, float, float] = DEFAULT_PLANE_AXIS
    shank_id: str = ""
    shape: str = DEFAULT_SHAPE
    extra: dict[str, AttrValue] = field(default_factory=dict)
    has_potentiostat_duplicate: bool = False
    has_intan_duplicate: bool = False
    has_manufacturer_duplicate: bool = False
    has_extra_duplicate: bool = False
    has_missing_pad: bool = False
    has_multiple_pads: bool = False

    def snapshot(self) -> ElectrodeSnapshot:
        """Return an immutable copy of editable fields."""
        return ElectrodeSnapshot(
            x=self.x,
            y=self.y,
            radius=self.radius,
            height=self.height,
            potentiostat_id=self.potentiostat_id,
            intan_id=self.intan_id,
            manufacturer_id=self.manufacturer_id,
            contact_plane_axis=self.contact_plane_axis,
            shank_id=self.shank_id,
            shape=self.shape,
            extra=dict(self.extra),
        )

    def restore(self, snap: ElectrodeSnapshot) -> None:
        """Apply a snapshot onto this model (keeps eid and duplicate flags)."""
        self.x = snap.x
        self.y = snap.y
        self.radius = snap.radius
        self.height = snap.height
        self.potentiostat_id = snap.potentiostat_id
        self.intan_id = snap.intan_id
        self.manufacturer_id = snap.manufacturer_id
        self.contact_plane_axis = snap.contact_plane_axis
        self.shank_id = snap.shank_id
        self.shape = snap.shape
        self.extra = dict(snap.extra)

    @classmethod
    def from_snapshot(cls, eid: int, snap: ElectrodeSnapshot) -> Electrode:
        """Build a new electrode from a snapshot."""
        return cls(
            eid=eid,
            x=snap.x,
            y=snap.y,
            radius=snap.radius,
            height=snap.height,
            potentiostat_id=snap.potentiostat_id,
            intan_id=snap.intan_id,
            manufacturer_id=snap.manufacturer_id,
            contact_plane_axis=snap.contact_plane_axis,
            shank_id=snap.shank_id,
            shape=snap.shape,
            extra=dict(snap.extra),
        )

    def get_attribute(self, key: str) -> AttrValue:
        """Read a built-in identifier or an extra attribute."""
        if key in BUILTIN_ATTRIBUTE_KEYS:
            return getattr(self, key)
        return self.extra.get(key, "")

    def set_attribute(self, key: str, value: AttrValue) -> None:
        """Write a built-in identifier or an extra attribute."""
        if key in BUILTIN_ATTRIBUTE_KEYS:
            setattr(self, key, value)
        else:
            self.extra[key] = value

    def map_center_label(self) -> str:
        """Compact identity: shank + potentiostat ID (combo boxes, etc.)."""
        return electrode_center_label(self.potentiostat_id, self.shank_id)

    def map_view_labels(
        self,
        visible_keys: Iterable[str] | None = None,
        schema_keys: Iterable[str] | None = None,
    ) -> tuple[str, str]:
        """Map-view labels from the visible electrode IDs."""
        order = list(BUILTIN_ATTRIBUTE_KEYS if schema_keys is None else schema_keys)
        keys = DEFAULT_MAP_LABEL_KEYS if visible_keys is None else visible_keys
        values: dict[str, AttrValue] = {key: self.get_attribute(key) for key in order}
        for key in keys:
            if key not in values:
                values[key] = self.get_attribute(key)
        return electrode_map_view_labels(values, keys, order)

    def has_any_duplicate(self) -> bool:
        """True if a pairing or identifier condition should highlight this electrode."""
        return (
            self.has_potentiostat_duplicate
            or self.has_intan_duplicate
            or self.has_manufacturer_duplicate
            or self.has_extra_duplicate
            or self.has_missing_pad
            or self.has_multiple_pads
        )
