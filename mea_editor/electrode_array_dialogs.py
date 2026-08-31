"""
Standalone dialogs used by the electrode array editor.

The goal of this module is to keep dialog code separated from the main window:
- clearer responsibilities,
- easier maintenance,
- easier reuse by other tools/scripts.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
)

from .attribute_schema import (
    UNIQUE_SCOPES,
    VALUE_TYPES,
    AttributeSpec,
    fallback_for_type,
    unique_extra_key,
)
from .contact_shape import (
    DEFAULT_ELECTRODE_SHAPE,
    DEFAULT_PAD_SHAPE,
    height_field_label,
    normalize_contact_shape,
    primary_size_field_label,
    shape_uses_height,
    size_field_from_stored_half,
    stored_half_from_size_field,
)
from .electrode import ELECTRODE_SHAPES
from .pad import (
    DEFAULT_PAD_RADIUS,
    PAD_SHAPES,
)

DEFAULT_ROWS = 8
DEFAULT_COLS = 8
DEFAULT_PITCH = 50.0
DEFAULT_UNITS = "um"
DEFAULT_PAD_ROWS = 1
DEFAULT_PAD_SPACING = 50.0


@dataclass(frozen=True)
class NewArrayParams:
    """Validated values from the new-array dialog."""

    rows: int
    cols: int
    pitch: float
    si_units: str
    electrode_shape: str
    pad_size: float
    pad_height: float
    pad_shape: str
    pad_rows: int
    pad_spacing: float


class NewArrayDialog(QDialog):
    """
    Single window used to create a new aligned array.

    Electrodes fill a regular grid. Pads form a rectangular frame around that
    grid, with user-defined size, shape, number of pad rows, and center-to-center
    spacing (same meaning as electrode pitch).
    """

    def __init__(self, parent=None) -> None:
        """
        Initialize new-array creation dialog.

        Args:
            parent: Parent window (optional).
        """
        super().__init__(parent)
        self.setWindowTitle("New Array Parameters")

        form = QFormLayout(self)

        electrode_header = QLabel("Electrodes")
        electrode_header.setStyleSheet("font-weight: bold;")
        form.addRow(electrode_header)

        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 512)
        self.rows_spin.setValue(DEFAULT_ROWS)
        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(1, 512)
        self.cols_spin.setValue(DEFAULT_COLS)
        self.pitch_spin = QDoubleSpinBox()
        self.pitch_spin.setRange(0.001, 100000.0)
        self.pitch_spin.setDecimals(3)
        self.pitch_spin.setValue(DEFAULT_PITCH)
        self.pitch_spin.setToolTip("Center-to-center distance between adjacent electrodes.")
        self.units_edit = QLineEdit(DEFAULT_UNITS)
        self.units_edit.setPlaceholderText("unit (e.g. um, mm)")
        self.electrode_shape_combo = QComboBox()
        self.electrode_shape_combo.addItems(list(ELECTRODE_SHAPES))
        self.electrode_shape_combo.setCurrentText(DEFAULT_ELECTRODE_SHAPE)

        form.addRow("Rows", self.rows_spin)
        form.addRow("Cols", self.cols_spin)
        form.addRow("Pitch", self.pitch_spin)
        form.addRow("si_units", self.units_edit)
        form.addRow("Shape", self.electrode_shape_combo)

        pad_header = QLabel("Pads (rectangle around electrodes)")
        pad_header.setStyleSheet("font-weight: bold;")
        form.addRow(pad_header)

        self.pad_size_spin = QDoubleSpinBox()
        self.pad_size_spin.setRange(0.001, 100000.0)
        self.pad_size_spin.setDecimals(3)
        self.pad_size_spin.setValue(size_field_from_stored_half(DEFAULT_PAD_SHAPE, DEFAULT_PAD_RADIUS))
        self.pad_height_spin = QDoubleSpinBox()
        self.pad_height_spin.setRange(0.001, 100000.0)
        self.pad_height_spin.setDecimals(3)
        self.pad_height_spin.setValue(size_field_from_stored_half("rect", DEFAULT_PAD_RADIUS))
        self.pad_shape_combo = QComboBox()
        self.pad_shape_combo.addItems(list(PAD_SHAPES))
        self.pad_shape_combo.setCurrentText(DEFAULT_PAD_SHAPE)
        self.pad_rows_spin = QSpinBox()
        self.pad_rows_spin.setRange(1, 32)
        self.pad_rows_spin.setValue(DEFAULT_PAD_ROWS)
        self.pad_spacing_spin = QDoubleSpinBox()
        self.pad_spacing_spin.setRange(0.001, 100000.0)
        self.pad_spacing_spin.setDecimals(3)
        self.pad_spacing_spin.setValue(DEFAULT_PAD_SPACING)
        self.pad_spacing_spin.setToolTip(
            "Center-to-center distance between adjacent pads, along a row and between rows."
        )

        self.pad_size_label = QLabel(primary_size_field_label(DEFAULT_PAD_SHAPE))
        self.pad_height_label = QLabel(height_field_label())
        self._pad_size_shape = DEFAULT_PAD_SHAPE
        self.pad_shape_combo.currentTextChanged.connect(self._on_pad_shape_changed)

        form.addRow("Shape", self.pad_shape_combo)
        form.addRow(self.pad_size_label, self.pad_size_spin)
        form.addRow(self.pad_height_label, self.pad_height_spin)
        form.addRow("Rows", self.pad_rows_spin)
        form.addRow("Spacing", self.pad_spacing_spin)
        self._form = form
        self._set_pad_height_visible(shape_uses_height(DEFAULT_PAD_SHAPE))

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _set_pad_height_visible(self, visible: bool) -> None:
        self.pad_height_label.setVisible(visible)
        self.pad_height_spin.setVisible(visible)
        self._form.setRowVisible(self.pad_height_spin, visible)

    def _on_pad_shape_changed(self, shape: str) -> None:
        """Keep the physical pad size and rename the field for the chosen geometry."""
        shape = normalize_contact_shape(shape, DEFAULT_PAD_SHAPE)
        stored = stored_half_from_size_field(self._pad_size_shape, self.pad_size_spin.value())
        self.pad_size_spin.setValue(size_field_from_stored_half(shape, stored))
        if shape_uses_height(shape):
            self.pad_height_spin.setValue(size_field_from_stored_half("rect", stored))
        self._pad_size_shape = shape
        self.pad_size_label.setText(primary_size_field_label(shape))
        self._set_pad_height_visible(shape_uses_height(shape))

    def values(self) -> NewArrayParams:
        """Return validated values from widgets."""
        units = self.units_edit.text().strip() or DEFAULT_UNITS
        electrode_shape = normalize_contact_shape(
            self.electrode_shape_combo.currentText(),
            DEFAULT_ELECTRODE_SHAPE,
        )
        shape = normalize_contact_shape(self.pad_shape_combo.currentText(), DEFAULT_PAD_SHAPE)
        pad_height = 0.0
        if shape_uses_height(shape):
            pad_height = stored_half_from_size_field("rect", self.pad_height_spin.value())
        return NewArrayParams(
            rows=self.rows_spin.value(),
            cols=self.cols_spin.value(),
            pitch=self.pitch_spin.value(),
            si_units=units,
            electrode_shape=electrode_shape,
            pad_size=stored_half_from_size_field(shape, self.pad_size_spin.value()),
            pad_height=pad_height,
            pad_shape=shape,
            pad_rows=self.pad_rows_spin.value(),
            pad_spacing=self.pad_spacing_spin.value(),
        )


class AddAttributeDialog(QDialog):
    """Dialog to add a file-level extra electrode attribute."""

    def __init__(self, schema: list[AttributeSpec], parent=None) -> None:
        super().__init__(parent)
        self._schema = list(schema)
        self.setWindowTitle("Add attribute")

        form = QFormLayout(self)
        self.name_edit = QLineEdit("")
        self.name_edit.setPlaceholderText("e.g. Connector pin")
        self.type_combo = QComboBox()
        self.type_combo.addItems(list(VALUE_TYPES))
        self.unique_check = QCheckBox("Must be unique")
        self.scope_combo = QComboBox()
        self.scope_combo.addItem("Globally", "global")
        self.scope_combo.addItem("Per shank", "per_shank")
        self.scope_combo.setEnabled(False)
        self.scope_combo.setToolTip("When unique, compare values across the whole array or only within each shank.")
        self.unique_check.toggled.connect(self.scope_combo.setEnabled)
        form.addRow("Name", self.name_edit)
        form.addRow("Type", self.type_combo)
        form.addRow(self.unique_check)
        form.addRow("Uniqueness", self.scope_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def spec(self) -> AttributeSpec | None:
        """Return the new spec, or None if the name is empty."""
        label = self.name_edit.text().strip()
        if not label:
            return None
        value_type = self.type_combo.currentText().strip().lower() or "str"
        if value_type not in VALUE_TYPES:
            value_type = "str"
        unique = self.unique_check.isChecked()
        unique_scope = self.scope_combo.currentData()
        if unique_scope not in UNIQUE_SCOPES:
            unique_scope = "global"
        return AttributeSpec(
            key=unique_extra_key(label, self._schema),
            label=label,
            value_type=value_type,
            default=fallback_for_type(value_type),
            builtin=False,
            unique=unique,
            unique_scope=unique_scope if unique else "global",
        )
