"""
MEA Editor - GUI and library to create and modify MEA arrays.

Native files use mea_editor JSON. SpikeInterface export writes probeinterface JSON.
XLSX exports cover analysis tables and the full electrode + pad workbook.
"""

from ._version import __version__
from .attribute_schema import AttributeSpec, default_schema
from .electrode import Electrode, ElectrodeSnapshot
from .electrode_array_editor_io import (
    export_analysis_xlsx,
    export_array_xlsx,
    export_spikeinterface_json,
    load_array_from_file,
    load_electrodes_from_file,
    save_array_to_file,
    save_electrodes_to_file,
)
from .electrode_array_editor_qt import ElectrodeArrayEditorQt, run_app
from .pad import Pad, PadSnapshot

__all__ = [
    "__version__",
    "AttributeSpec",
    "Electrode",
    "ElectrodeSnapshot",
    "Pad",
    "PadSnapshot",
    "default_schema",
    "load_array_from_file",
    "load_electrodes_from_file",
    "save_array_to_file",
    "save_electrodes_to_file",
    "export_spikeinterface_json",
    "export_analysis_xlsx",
    "export_array_xlsx",
    "ElectrodeArrayEditorQt",
    "run_app",
]
