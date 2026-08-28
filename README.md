# MEA-Editor

GUI to create and modify MEA (Multi-Electrode Arrays).

Arrays are saved in a native JSON format. Optional exports produce:

- a [probeinterface](https://probeinterface.readthedocs.io/) JSON for [SpikeInterface](https://spikeinterface.readthedocs.io/)
- an analysis XLSX (`channel`, `row`, `col`, …)
- a full array XLSX (electrodes, pads, attribute schema)

**Multi-platform:** Windows, macOS, Linux.

The library is available on PyPI.

## Installation (PyPI)
1. Open terminal as administrator
2. Run on terminal [uv](https://docs.astral.sh/uv/): `curl -LsSf https://astral.sh/uv/install.sh | sh` (macOS/Linux) or `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"` (Windows)
3. Install virtual environment : run in terminal `uv venv si_env --python 3.12`
4. Restart your terminal
5. Allow script execution : run in terminal `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned`
6. Activate virtual environment: run in terminal `source si_env/bin/activate` (macOS/Linux) or `si_env\Scripts\activate` (Windows)
7. Install library : run in terminal `uv pip install mea-editor`

## Run application
1. Allow script execution : run in terminal `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned`
2. Activate virtual environment: run in terminal `source si_env/bin/activate` (macOS/Linux) or `si_env\Scripts\activate` (Windows)
3. Run in terminal `mea-editor`

## Mapping views
The scene is shared. Two cameras sit side by side:

- **Electrodes** (left): fitted to the electrode cluster
- **Pads** (right): fitted to the pad frame

Each view keeps its own zoom and pan. **Fit View** (`Ctrl+0`) fits both cameras.

## Identifiers
Each electrode stores built-in identifiers:
- **Potentiostat ID** (integer)
- **INTAN ID** (e.g. `A-003`)
- **Manufacturer ID** (optional unique contact label)
- **Shank ID**

The center label shows the Potentiostat ID; the label under the contact shows the INTAN ID. If a shank is set, the center label is `<shank>-<potentiostat>`.

Extra electrode attributes can be added with **Add attribute**. They belong to the array file (`electrode_attributes` in the JSON). Opening a file rebuilds the side panel from that list, so arrays can have more or fewer fields.

## Shapes
Electrodes and pads use the three SpikeInterface contact geometries: `circle`, `square`, `rect`. For `rect`, Width and Height are independent.

## Pads
Pads are connector interfaces toward other electronic systems. They appear in the pad view, each linked to one electrode. Pads have no numbers of their own: the map shows the associated electrode's Potentiostat / shank / INTAN labels. Pad fields:
- **Electrode** (required association, identified by Potentiostat / shank / INTAN)
- **Interface ID** (pin / connector identifier)
- **System ID** (optional name of the target electronic system)

The side panel has two parameterization tabs: **Electrodes** and **Pads**.

## Native save (File > Save)
`File > Save` / `Save As` writes mea_editor JSON (`specification: "mea_editor"`, version `1.4`):
- `si_units`
- `electrode_attributes` (built-in + extra fields)
- `electrodes` (geometry, shape, height, identifiers, extras)
- `pads` (geometry, shape, height, electrode link, interface / system IDs)

This is the format to keep as the source of truth. Probeinterface JSON can still be opened (migrated into native fields). Saving then writes native JSON.

## SpikeInterface export
`File > Export for SpikeInterface...` writes a probeinterface JSON for **recording contacts only** (pads are not SpikeInterface contacts):
- **channel ID** (`device_channel_indices`) is derived from INTAN ID (`A-003` → 3, `D-018` → 114, `NC` → -1)
- **Contact ID** (`contact_ids`) is Manufacturer ID, or INTAN ID if Manufacturer ID is unused
- `contact_shapes` / `contact_shape_params` follow SpikeInterface (`circle` / `square` / `rect`)
- `contact_annotations` stores native IDs, extra attributes, and the first linked pad (`pad_interface_id`, `pad_system_id`) so a file exported from this editor can be reopened with less data loss

Existing probeinterface JSON files can still be opened. Pads are native-only: they are restored from mea_editor JSON, not from SpikeInterface JSON.

## XLSX exports
- **Export for analysis...**: sheet `array`, starting with `channel`, `row`, `col`, `shape`, then INTAN / manufacturer / shank / extras / linked pad IDs
- **Export array as XLSX...**: sheet `array` (full electrode table), sheet `pads`, sheet `electrode_attributes`

`row` is electrode Y, `col` is electrode X.

## Build a standalone executable (Windows: `.exe`, macOS/Linux: binary):
1. Allow script execution : run in terminal `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned`
2. Activate virtual environment: run in terminal `source si_env/bin/activate` (macOS/Linux) or `si_env\Scripts\activate` (Windows)
3. Using the command-line terminal, navigate to the folder where you want the .exe file to be located.
4. Build the executable in currentfolder/dist : run in terminal `mea-editor-build`

The executable will be in `dist/` (in the current directory).
