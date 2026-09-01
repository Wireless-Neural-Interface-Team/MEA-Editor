"""
Identifier uniqueness, INTAN channel collisions, and electrode/pad pairing.

Used by the editor for red highlighting and by tests without spinning the GUI.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from .attribute_schema import AttributeSpec, extra_specs
from .electrode import Electrode
from .electrode_array_editor_io import try_intan_channel_id
from .orientation_marker import OrientationMarker
from .pad import Pad


def ensure_unique_model_ids(models: list[Electrode], pads: list[Pad]) -> tuple[int, int]:
    """
    Reassign colliding electrode/pad ids so dictionaries stay 1:1.

    The first occurrence of an id is kept. Later duplicates get the next free id.
    Pads keep `electrode_eid` as stored (they stay attached to whoever kept that
    eid). Returns ``(n_electrode_ids_changed, n_pad_ids_changed)``.
    """
    eid_changes = 0
    used_eids: set[int] = set()
    next_eid = 0
    for model in models:
        if model.eid in used_eids:
            while next_eid in used_eids:
                next_eid += 1
            model.eid = next_eid
            eid_changes += 1
        used_eids.add(model.eid)
        next_eid = max(next_eid, model.eid + 1)

    pad_id_changes = 0
    used_pad_ids: set[int] = set()
    next_pad_id = 0
    for pad in pads:
        if pad.pad_id in used_pad_ids:
            while next_pad_id in used_pad_ids:
                next_pad_id += 1
            pad.pad_id = next_pad_id
            pad_id_changes += 1
        used_pad_ids.add(pad.pad_id)
        next_pad_id = max(next_pad_id, pad.pad_id + 1)

    return eid_changes, pad_id_changes


def ensure_unique_marker_ids(markers: list[OrientationMarker]) -> int:
    """
    Reassign colliding orientation-marker ids so dictionaries stay 1:1.

    The first occurrence of an id is kept. Later duplicates get the next free id.
    Returns the number of ids that were changed.
    """
    changes = 0
    used: set[int] = set()
    next_id = 0
    for marker in markers:
        if marker.marker_id in used:
            while next_id in used:
                next_id += 1
            marker.marker_id = next_id
            changes += 1
        used.add(marker.marker_id)
        next_id = max(next_id, marker.marker_id + 1)
    return changes


def pairing_problems(electrodes: Iterable[Electrode], pads: Iterable[Pad]) -> list[str]:
    """Human-readable 1:1 pairing issues, if any."""
    electrode_list = list(electrodes)
    pad_list = list(pads)
    valid_eids = {model.eid for model in electrode_list}
    counts = Counter(pad.electrode_eid for pad in pad_list if pad.electrode_eid in valid_eids)
    problems: list[str] = []
    missing_pads = sum(1 for model in electrode_list if model.eid not in counts)
    if missing_pads:
        problems.append(f"{missing_pads} electrode(s) have no pad.")
    shared = sum(1 for count in counts.values() if count > 1)
    if shared:
        problems.append(f"{shared} electrode(s) are linked to more than one pad.")
    missing_electrodes = sum(1 for pad in pad_list if pad.electrode_eid not in valid_eids)
    if missing_electrodes:
        problems.append(f"{missing_electrodes} pad(s) have no associated electrode.")
    return problems


def refresh_status_flags(
    electrodes: Iterable[Electrode],
    pads: Iterable[Pad],
    schema: Iterable[AttributeSpec],
) -> None:
    """
    Recompute identifier and pairing flags on the given models.

    - Potentiostat ID uniqueness is per shank.
    - INTAN uniqueness is on the SpikeInterface channel ID (so A-003, A003 and 3
      collide; A-032 is invalid). Empty or unparseable INTAN IDs are flagged.
    - Manufacturer ID: duplicates among non-empty values; if any is filled,
      empty ones are also flagged (SpikeInterface all-or-nothing rule).
    - Extra unique attributes follow schema unique_scope.
    - Pairing: missing/shared electrode or pad.
    """
    electrode_list = list(electrodes)
    pad_list = list(pads)

    potentiostat_key_counts = Counter(
        (str(model.shank_id).strip(), model.potentiostat_id) for model in electrode_list
    )
    duplicate_potentiostat_keys = {key for key, count in potentiostat_key_counts.items() if count > 1}

    channel_owners: dict[int, list[int]] = {}
    invalid_intan_eids: set[int] = set()
    for model in electrode_list:
        text = str(model.intan_id).strip()
        if not text:
            invalid_intan_eids.add(model.eid)
            continue
        channel = try_intan_channel_id(text)
        if channel is None:
            invalid_intan_eids.add(model.eid)
            continue
        if channel < 0:
            continue
        channel_owners.setdefault(channel, []).append(model.eid)
    duplicate_intan_eids = {
        eid for eids in channel_owners.values() if len(eids) > 1 for eid in eids
    }

    manufacturer_counts = Counter(model.manufacturer_id for model in electrode_list)
    duplicate_manufacturer = {
        value for value, count in manufacturer_counts.items() if count > 1 and str(value).strip() != ""
    }
    any_manufacturer = any(str(model.manufacturer_id).strip() for model in electrode_list)

    for model in electrode_list:
        model_key = (str(model.shank_id).strip(), model.potentiostat_id)
        model.has_potentiostat_duplicate = model_key in duplicate_potentiostat_keys
        model.has_intan_duplicate = model.eid in duplicate_intan_eids or model.eid in invalid_intan_eids
        empty_manufacturer = str(model.manufacturer_id).strip() == ""
        model.has_manufacturer_duplicate = (
            model.manufacturer_id in duplicate_manufacturer
            or (any_manufacturer and empty_manufacturer)
        )
        model.has_extra_duplicate = False

    for spec in extra_specs(schema):
        if not spec.unique:
            continue
        if spec.unique_scope == "per_shank":
            counts = Counter(
                (str(model.shank_id).strip(), model.get_attribute(spec.key)) for model in electrode_list
            )
            duplicates = {key for key, count in counts.items() if count > 1 and str(key[1]).strip() != ""}
            for model in electrode_list:
                key = (str(model.shank_id).strip(), model.get_attribute(spec.key))
                if key in duplicates:
                    model.has_extra_duplicate = True
            continue
        counts = Counter(model.get_attribute(spec.key) for model in electrode_list)
        duplicates = {value for value, count in counts.items() if count > 1 and str(value).strip() != ""}
        if not duplicates:
            continue
        for model in electrode_list:
            if model.get_attribute(spec.key) in duplicates:
                model.has_extra_duplicate = True

    valid_eids = {model.eid for model in electrode_list}
    electrode_pad_counts = Counter(
        pad.electrode_eid for pad in pad_list if pad.electrode_eid in valid_eids
    )
    shared_electrodes = {eid for eid, count in electrode_pad_counts.items() if count > 1}
    paired_electrodes = set(electrode_pad_counts)
    for pad in pad_list:
        pad.has_missing_electrode = pad.electrode_eid not in valid_eids
        pad.has_shared_electrode = pad.electrode_eid in shared_electrodes
    for model in electrode_list:
        model.has_missing_pad = model.eid not in paired_electrodes
        model.has_multiple_pads = electrode_pad_counts.get(model.eid, 0) > 1
