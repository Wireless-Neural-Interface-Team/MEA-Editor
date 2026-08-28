"""
Non-modal electrode table window.

Shows every electrode (geometry, identifiers, extra attributes, linked pad)
in a sortable table. Search and per-attribute filters hide rows. Selecting a
row selects that electrode and its pad in the mapping views.
"""

from __future__ import annotations

from typing import Any, Iterable

from PySide6.QtCore import (
    QAbstractTableModel,
    QItemSelection,
    QItemSelectionModel,
    QModelIndex,
    QSortFilterProxyModel,
    Qt,
    Signal,
)
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from .attribute_schema import AttributeSpec
from .electrode import Electrode
from .pad import Pad

ALL_FILTER = "(all)"
EMPTY_FILTER = "(empty)"
EID_ROLE = Qt.UserRole
SORT_ROLE = Qt.UserRole + 1

FIXED_COLUMNS: tuple[tuple[str, str], ...] = (
    ("eid", "ID"),
    ("x", "X"),
    ("y", "Y"),
    ("shape", "Shape"),
    ("radius", "Radius"),
    ("height", "Height"),
    ("enabled", "Enabled"),
    ("contact_plane_axis", "Contact plane"),
)
PAD_COLUMNS: tuple[tuple[str, str], ...] = (
    ("pad_pid", "Pad ID"),
    ("pad_interface_id", "Interface ID"),
    ("pad_system_id", "System ID"),
)


def pads_by_electrode(pads: Iterable[Pad] | None) -> dict[int, Pad]:
    """Map each electrode eid to its first pad (lowest pid)."""
    mapping: dict[int, Pad] = {}
    for pad in sorted(pads or [], key=lambda item: item.pid):
        mapping.setdefault(pad.electrode_eid, pad)
    return mapping


def table_columns(schema: Iterable[AttributeSpec]) -> list[tuple[str, str]]:
    """Column keys and labels: geometry, schema attributes, linked pad."""
    columns = list(FIXED_COLUMNS)
    columns.extend((spec.key, spec.label) for spec in schema)
    columns.extend(PAD_COLUMNS)
    return columns


def format_cell(value: Any) -> str:
    """Display text for a table cell."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def format_plane_axis(axis: tuple[float, float, float, float]) -> str:
    return ", ".join(f"{value:g}" for value in axis)


def electrode_row(
    model: Electrode,
    pad: Pad | None,
    schema: Iterable[AttributeSpec],
) -> dict[str, Any]:
    """Raw values for one table row, keyed by column key."""
    row: dict[str, Any] = {
        "eid": int(model.eid),
        "x": float(model.x),
        "y": float(model.y),
        "shape": str(model.shape),
        "radius": float(model.radius),
        "height": float(model.height),
        "enabled": bool(model.enabled),
        "contact_plane_axis": format_plane_axis(model.contact_plane_axis),
        "pad_pid": int(pad.pid) if pad is not None else None,
        "pad_interface_id": pad.interface_id if pad is not None else "",
        "pad_system_id": pad.system_id if pad is not None else "",
    }
    for spec in schema:
        row[spec.key] = model.get_attribute(spec.key)
    return row


def row_matches(
    display_values: Iterable[str],
    search: str,
    attribute_filters: dict[str, str],
    attribute_display: dict[str, str],
) -> bool:
    """True when a row passes the search box and per-attribute combo filters."""
    query = search.strip().lower()
    if query and not any(query in text.lower() for text in display_values):
        return False
    for key, required in attribute_filters.items():
        if not required or required == ALL_FILTER:
            continue
        actual = attribute_display.get(key, "")
        token = actual if actual else EMPTY_FILTER
        if token != required:
            return False
    return True


def unique_attribute_values(rows: Iterable[dict[str, Any]], key: str) -> list[str]:
    """Sorted unique display tokens for one attribute filter combo."""
    tokens: set[str] = set()
    for row in rows:
        text = format_cell(row.get(key, ""))
        tokens.add(text if text else EMPTY_FILTER)
    return sorted(tokens, key=lambda item: (item == EMPTY_FILTER, item.lower()))


class ElectrodeTableModel(QAbstractTableModel):
    """Flat table of electrode fields plus the associated pad."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._columns: list[tuple[str, str]] = []
        self._rows: list[dict[str, Any]] = []
        self._key_to_col: dict[str, int] = {}

    def reload(
        self,
        electrodes: Iterable[Electrode],
        pads: Iterable[Pad],
        schema: Iterable[AttributeSpec],
    ) -> None:
        schema_list = list(schema)
        columns = table_columns(schema_list)
        pad_map = pads_by_electrode(pads)
        rows = [
            electrode_row(model, pad_map.get(model.eid), schema_list)
            for model in sorted(electrodes, key=lambda item: (item.potentiostat_id, item.eid))
        ]
        self.beginResetModel()
        self._columns = columns
        self._rows = rows
        self._key_to_col = {key: index for index, (key, _label) in enumerate(columns)}
        self.endResetModel()

    def column_index(self, key: str) -> int:
        return self._key_to_col.get(key, -1)

    def row_at(self, row: int) -> dict[str, Any] | None:
        if 0 <= row < len(self._rows):
            return self._rows[row]
        return None

    def eid_at(self, row: int) -> int | None:
        data = self.row_at(row)
        if data is None:
            return None
        return int(data["eid"])

    def rows_data(self) -> list[dict[str, Any]]:
        return self._rows

    def column_keys(self) -> list[str]:
        return [key for key, _label in self._columns]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # type: ignore[override]
        if parent.isValid():
            return 0
        return len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # type: ignore[override]
        if parent.isValid():
            return 0
        return len(self._columns)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):  # type: ignore[override]
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal and 0 <= section < len(self._columns):
            return self._columns[section][1]
        if orientation == Qt.Vertical and 0 <= section < len(self._rows):
            return section + 1
        return None

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):  # type: ignore[override]
        if not index.isValid():
            return None
        row = self.row_at(index.row())
        if row is None:
            return None
        key = self._columns[index.column()][0]
        raw = row.get(key, "")
        if role == Qt.DisplayRole:
            return format_cell(raw)
        if role == SORT_ROLE:
            return raw
        if role == EID_ROLE:
            return int(row["eid"])
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:  # type: ignore[override]
        if not index.isValid():
            return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable


class ElectrodeTableFilterProxy(QSortFilterProxyModel):
    """Search-all-columns plus exact match on selected attribute values."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._search = ""
        self._attribute_filters: dict[str, str] = {}
        self.setSortRole(SORT_ROLE)
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)

    def set_search(self, text: str) -> None:
        self._search = text
        self.invalidateFilter()

    def set_attribute_filter(self, key: str, value: str) -> None:
        self._attribute_filters[key] = value
        self.invalidateFilter()

    def clear_attribute_filters(self) -> None:
        self._attribute_filters.clear()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:  # type: ignore[override]
        model = self.sourceModel()
        if not isinstance(model, ElectrodeTableModel):
            return True
        row = model.row_at(source_row)
        if row is None:
            return False
        display_values = [format_cell(row.get(key, "")) for key in model.column_keys()]
        attribute_display = {
            key: format_cell(row.get(key, ""))
            for key in self._attribute_filters
        }
        return row_matches(display_values, self._search, self._attribute_filters, attribute_display)


class ElectrodeTableWindow(QWidget):
    """
    Independent, non-modal window listing all electrodes.

    The main editor stays usable while this window is open.
    """

    electrodes_chosen = Signal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            parent,
            Qt.Tool | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowMaximizeButtonHint,
        )
        self.setWindowTitle("Electrode table")
        self.setWindowModality(Qt.NonModal)
        self.setAttribute(Qt.WA_QuitOnClose, False)
        self.resize(980, 520)

        self._schema: list[AttributeSpec] = []
        self._syncing_selection = False
        self._filter_combos: dict[str, QComboBox] = {}

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search all columns…")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setToolTip("Show rows whose any field contains this text.")

        self.count_label = QLabel("0 / 0 electrodes")

        b_clear = QPushButton("Clear filters")
        b_clear.setAutoDefault(False)
        b_clear.clicked.connect(self._clear_filters)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Search"))
        search_row.addWidget(self.search_edit, stretch=1)
        search_row.addWidget(b_clear)
        search_row.addWidget(self.count_label)

        self.filters_box = QGroupBox("Attribute filters")
        self.filters_inner = QWidget()
        self.filters_layout = QHBoxLayout(self.filters_inner)
        self.filters_layout.setContentsMargins(0, 0, 0, 0)
        self.filters_layout.setSpacing(8)
        filters_scroll = QScrollArea()
        filters_scroll.setWidgetResizable(True)
        filters_scroll.setFrameShape(QFrame.NoFrame)
        filters_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        filters_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        filters_scroll.setWidget(self.filters_inner)
        filters_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        filters_scroll.setMaximumHeight(72)
        filters_box_layout = QVBoxLayout(self.filters_box)
        filters_box_layout.setContentsMargins(8, 8, 8, 8)
        filters_box_layout.addWidget(filters_scroll)

        self.model = ElectrodeTableModel(self)
        self.proxy = ElectrodeTableFilterProxy(self)
        self.proxy.setSourceModel(self.model)

        self.table = QTableView(self)
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setStretchLastSection(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.addLayout(search_row)
        layout.addWidget(self.filters_box)
        layout.addWidget(self.table, stretch=1)

        self.search_edit.textChanged.connect(self._on_search_changed)
        self.table.selectionModel().selectionChanged.connect(self._on_table_selection_changed)

    def reload(
        self,
        electrodes: Iterable[Electrode],
        pads: Iterable[Pad],
        schema: Iterable[AttributeSpec],
        selected_eids: Iterable[int] | None = None,
    ) -> None:
        """Rebuild rows/columns from the current array, keeping filters when possible."""
        schema_list = list(schema)
        previous_filters = {
            key: combo.currentText()
            for key, combo in self._filter_combos.items()
        }
        selected = set(selected_eids) if selected_eids is not None else self.selected_eids()
        header = self.table.horizontalHeader()
        sort_col = header.sortIndicatorSection()
        sort_order = header.sortIndicatorOrder()

        self._syncing_selection = True
        try:
            self._schema = schema_list
            self.proxy.clear_attribute_filters()
            self.model.reload(electrodes, pads, schema_list)
            self._rebuild_filter_combos(previous_filters)
            if 0 <= sort_col < self.proxy.columnCount():
                self.proxy.sort(sort_col, sort_order)
            self._fit_columns()
            self._update_count()
        finally:
            self._syncing_selection = False
        self.set_selected_eids(selected)

    def selected_eids(self) -> set[int]:
        eids: set[int] = set()
        selection = self.table.selectionModel()
        if selection is None:
            return eids
        for index in selection.selectedRows():
            eid = index.data(EID_ROLE)
            if eid is not None:
                eids.add(int(eid))
        return eids

    def set_selected_eids(self, eids: Iterable[int]) -> None:
        """Highlight table rows for the given electrode ids without emitting a choice."""
        wanted = {int(eid) for eid in eids}
        if wanted == self.selected_eids():
            return
        selection_model = self.table.selectionModel()
        if selection_model is None:
            return
        self._syncing_selection = True
        try:
            selection = QItemSelection()
            first_index: QModelIndex | None = None
            for row in range(self.proxy.rowCount()):
                index = self.proxy.index(row, 0)
                eid = index.data(EID_ROLE)
                if eid is None or int(eid) not in wanted:
                    continue
                last = self.proxy.index(row, max(self.proxy.columnCount() - 1, 0))
                selection.select(index, last)
                if first_index is None:
                    first_index = index
            selection_model.select(
                selection,
                QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows,
            )
            if first_index is not None:
                self.table.scrollTo(first_index)
        finally:
            self._syncing_selection = False

    def closeEvent(self, event) -> None:  # type: ignore[override]
        event.ignore()
        self.hide()

    def _fit_columns(self) -> None:
        self.table.resizeColumnsToContents()

    def _rebuild_filter_combos(self, previous: dict[str, str]) -> None:
        for combo in self._filter_combos.values():
            combo.blockSignals(True)
        while self.filters_layout.count():
            item = self.filters_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._filter_combos.clear()
        rows = self.model.rows_data()
        for spec in self._schema:
            combo = QComboBox()
            combo.setMinimumWidth(110)
            combo.setMaxVisibleItems(20)
            combo.addItem(ALL_FILTER)
            combo.addItems(unique_attribute_values(rows, spec.key))
            wanted = previous.get(spec.key, ALL_FILTER)
            index = combo.findText(wanted)
            combo.setCurrentIndex(index if index >= 0 else 0)
            combo.currentTextChanged.connect(
                lambda text, key=spec.key: self._on_attribute_filter_changed(key, text)
            )
            self.proxy.set_attribute_filter(spec.key, combo.currentText())
            self._filter_combos[spec.key] = combo
            cell = QWidget()
            cell_layout = QVBoxLayout(cell)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.setSpacing(2)
            label = QLabel(spec.label)
            cell_layout.addWidget(label)
            cell_layout.addWidget(combo)
            self.filters_layout.addWidget(cell)
        self.filters_layout.addStretch(1)

    def _on_search_changed(self, text: str) -> None:
        self.proxy.set_search(text)
        self._update_count()

    def _on_attribute_filter_changed(self, key: str, text: str) -> None:
        self.proxy.set_attribute_filter(key, text)
        self._update_count()

    def _clear_filters(self) -> None:
        self.search_edit.clear()
        for key, combo in self._filter_combos.items():
            combo.blockSignals(True)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)
            self.proxy.set_attribute_filter(key, ALL_FILTER)
        self._update_count()

    def _update_count(self) -> None:
        visible = self.proxy.rowCount()
        total = self.model.rowCount()
        self.count_label.setText(f"{visible} / {total} electrodes")

    def _on_table_selection_changed(self, *_args) -> None:
        if self._syncing_selection:
            return
        eids = sorted(self.selected_eids())
        self.electrodes_chosen.emit(eids)
