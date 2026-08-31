"""
File-level electrode attribute schema.

Built-in identifiers (Potentiostat ID, INTAN ID, Manufacturer ID, Shank ID)
are always present. Extra attributes are defined per file: they are stored
in the native JSON and the editor UI rebuilds itself from that list.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable

from .electrode import (
    BUILTIN_ATTRIBUTE_KEYS,
    DEFAULT_INTAN_ID,
    DEFAULT_MANUFACTURER_ID,
    Electrode,
)

AttrValue = str | int | float
VALUE_TYPES = ("str", "int", "float")
UNIQUE_SCOPES = ("global", "per_shank")

_KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_RESERVED_KEYS = frozenset(
    {
        *BUILTIN_ATTRIBUTE_KEYS,
        "eid",
        "x",
        "y",
        "radius",
        "height",
        "enabled",  # dropped field; keep reserved so old files do not create an extra
        "shape",
        "contact_plane_axis",
        "channel_index",
        "contact_id",
        "attributes",
        "extra",
        "pid",
        "pad_id",
        "electrode_eid",
        "interface_id",
        "system_id",
        "mea_editor_electrode_attributes",
    }
)


@dataclass(frozen=True, slots=True)
class AttributeSpec:
    """One electrode attribute: built-in identifier or file-defined extra field."""

    key: str
    label: str
    value_type: str = "str"
    default: AttrValue = ""
    builtin: bool = False
    unique: bool = False
    unique_scope: str = "global"

    def to_dict(self) -> dict[str, Any]:
        """Serialize this spec for native JSON."""
        return {
            "key": self.key,
            "label": self.label,
            "type": self.value_type,
            "default": self.default,
            "builtin": self.builtin,
            "unique": self.unique,
            "unique_scope": self.unique_scope,
        }

    @classmethod
    def from_dict(cls, raw: Any) -> AttributeSpec | None:
        """Parse a spec from JSON. Invalid entries are ignored."""
        if not isinstance(raw, dict):
            return None
        key = str(raw.get("key", "")).strip()
        if not key:
            return None
        label = str(raw.get("label", "")).strip() or key.replace("_", " ").title()
        value_type = str(raw.get("type", "str")).strip().lower() or "str"
        if value_type not in VALUE_TYPES:
            value_type = "str"
        unique_scope = str(raw.get("unique_scope", "global")).strip().lower() or "global"
        if unique_scope not in UNIQUE_SCOPES:
            unique_scope = "global"
        default = coerce_value(value_type, raw.get("default"), fallback_for_type(value_type))
        return cls(
            key=key,
            label=label,
            value_type=value_type,
            default=default,
            builtin=bool(raw.get("builtin", False)),
            unique=bool(raw.get("unique", False)),
            unique_scope=unique_scope,
        )


DEFAULT_ELECTRODE_ATTRIBUTES: tuple[AttributeSpec, ...] = (
    AttributeSpec(
        key="potentiostat_id",
        label="Potentiostat ID",
        value_type="int",
        default=0,
        builtin=True,
        unique=True,
        unique_scope="per_shank",
    ),
    AttributeSpec(
        key="intan_id",
        label="INTAN ID",
        value_type="str",
        default=DEFAULT_INTAN_ID,
        builtin=True,
        unique=True,
        unique_scope="global",
    ),
    AttributeSpec(
        key="manufacturer_id",
        label="Manufacturer ID",
        value_type="str",
        default=DEFAULT_MANUFACTURER_ID,
        builtin=True,
        unique=True,
        unique_scope="global",
    ),
    AttributeSpec(
        key="shank_id",
        label="Shank ID",
        value_type="str",
        default="",
        builtin=True,
        unique=False,
        unique_scope="global",
    ),
)

_BUILTIN_BY_KEY = {spec.key: spec for spec in DEFAULT_ELECTRODE_ATTRIBUTES}


def default_schema() -> list[AttributeSpec]:
    """Return a fresh copy of the built-in identifier schema."""
    return list(DEFAULT_ELECTRODE_ATTRIBUTES)


def extra_specs(schema: Iterable[AttributeSpec]) -> list[AttributeSpec]:
    """Return non-built-in specs in schema order."""
    return [spec for spec in schema if not spec.builtin]


def fallback_for_type(value_type: str) -> AttrValue:
    if value_type == "int":
        return 0
    if value_type == "float":
        return 0.0
    return ""


def coerce_value(value_type: str, raw: Any, default: AttrValue | None = None) -> AttrValue:
    """Coerce a JSON/UI value to the spec type, or return default on failure."""
    if default is None:
        default = fallback_for_type(value_type)
    if raw is None:
        return default
    try:
        if value_type == "int":
            if isinstance(raw, bool):
                return default
            if isinstance(raw, str) and not raw.strip():
                return default
            return int(raw)
        if value_type == "float":
            if isinstance(raw, bool):
                return default
            if isinstance(raw, str) and not raw.strip():
                return default
            return float(raw)
        text = str(raw)
        return text
    except (TypeError, ValueError):
        return default


def parse_user_value(spec: AttributeSpec, text: str) -> AttrValue:
    """
    Parse a non-empty UI string into the spec type.

    Raises:
        ValueError: if the text cannot be converted.
    """
    stripped = text.strip()
    if spec.value_type == "int":
        return int(stripped)
    if spec.value_type == "float":
        return float(stripped)
    return text if spec.value_type != "str" else stripped


def slugify_attribute_key(label: str) -> str:
    """Turn a display label into a snake_case JSON key."""
    text = label.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = text.strip("_")
    if not text or not text[0].isalpha():
        text = f"attr_{text}" if text else "attr"
        text = text.strip("_") or "attr"
    return text


def is_valid_extra_key(key: str) -> bool:
    return bool(_KEY_RE.fullmatch(key)) and key not in _RESERVED_KEYS


def unique_extra_key(label: str, schema: Iterable[AttributeSpec]) -> str:
    """Build a unique extra key from a label, avoiding reserved and existing keys."""
    existing = {spec.key for spec in schema} | _RESERVED_KEYS
    base = slugify_attribute_key(label)
    if not _KEY_RE.fullmatch(base):
        base = "attr"
    key = base
    n = 2
    while key in existing:
        key = f"{base}_{n}"
        n += 1
    return key


def fill_electrode_extras(model: Electrode, schema: Iterable[AttributeSpec], *, prune: bool = False) -> None:
    """Ensure extra dict has an entry for every extra spec (optionally drop unknown keys)."""
    extras = extra_specs(schema)
    extra_keys = {spec.key for spec in extras}
    for spec in extras:
        if spec.key not in model.extra:
            model.extra[spec.key] = spec.default
        else:
            model.extra[spec.key] = coerce_value(spec.value_type, model.extra[spec.key], spec.default)
    if prune:
        for key in list(model.extra):
            if key not in extra_keys:
                del model.extra[key]


def fill_electrodes_extras(
    electrodes: Iterable[Electrode],
    schema: Iterable[AttributeSpec],
    *,
    prune: bool = False,
) -> None:
    for model in electrodes:
        fill_electrode_extras(model, schema, prune=prune)


def infer_extra_specs(electrodes: Iterable[Electrode], schema: Iterable[AttributeSpec]) -> list[AttributeSpec]:
    """Create extra specs for keys present on electrodes but missing from the schema."""
    known = {spec.key for spec in schema} | set(BUILTIN_ATTRIBUTE_KEYS)
    inferred: list[AttributeSpec] = []
    for model in electrodes:
        for key, value in model.extra.items():
            if key in known or not key:
                continue
            value_type = _type_of(value)
            inferred.append(
                AttributeSpec(
                    key=key,
                    label=key.replace("_", " ").title(),
                    value_type=value_type,
                    default=fallback_for_type(value_type),
                    builtin=False,
                    unique=False,
                )
            )
            known.add(key)
    return inferred


def schema_from_payload(raw_list: Any, electrodes: Iterable[Electrode] | None = None) -> list[AttributeSpec]:
    """
    Build a schema from native JSON.

    Built-in identifiers are always included (fixed meaning). Extra specs come
    from the file list, then from any leftover electrode extra keys.
    """
    schema = default_schema()
    seen_extra: set[str] = set()
    if isinstance(raw_list, list):
        for item in raw_list:
            spec = AttributeSpec.from_dict(item)
            if spec is None or spec.builtin or spec.key in _BUILTIN_BY_KEY:
                continue
            if spec.key in seen_extra or not spec.key:
                continue
            # Extra keys must not collide with reserved geometry / I/O names.
            if spec.key in _RESERVED_KEYS:
                continue
            schema.append(
                AttributeSpec(
                    key=spec.key,
                    label=spec.label,
                    value_type=spec.value_type,
                    default=spec.default,
                    builtin=False,
                    unique=spec.unique,
                    unique_scope="global" if spec.unique_scope not in UNIQUE_SCOPES else spec.unique_scope,
                )
            )
            seen_extra.add(spec.key)
    if electrodes is not None:
        schema.extend(infer_extra_specs(electrodes, schema))
    return schema


def schema_to_payload(schema: Iterable[AttributeSpec]) -> list[dict[str, Any]]:
    return [spec.to_dict() for spec in schema]


def _type_of(value: Any) -> str:
    if isinstance(value, bool):
        return "str"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    return "str"
