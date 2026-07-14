# Hyperscanning Toolkit

**Version 1.0.0**

A config-driven pipeline for building inter-brain (dyadic) and intra-brain
functional connectivity graphs from hyperscanning timeseries data. The core
package makes no assumptions about signal modality (fNIRS, EEG, ECG, GSR, ...),
epoch/marker scheme, or folder layout — every dataset-specific detail lives in
one YAML config file.

See [`examples/3hyper_mother_infant/`](examples/3hyper_mother_infant/) for a
full worked example (a mother-infant fNIRS hyperscanning dataset) including
the adapter script and config that reproduce it.

## Install

```bash
pip install -e .
```

## Basic usage example

```python
from hyperscanning_toolkit.config import ToolkitConfig
from hyperscanning_toolkit.pipeline import run_all

cfg = ToolkitConfig.from_yaml("config.yaml")
result = run_all(cfg)          # runs inspect -> extract -> graphs

print(result["summary"].render())   # human-readable run summary
result["intra"]                      # DataFrame of intra-brain graph metrics
result["inter"]                      # DataFrame of inter-brain graph metrics
```

## CLI usage

```bash
python -m hyperscanning_toolkit --config config.yaml run     # inspect -> extract -> graphs
python -m hyperscanning_toolkit --config config.yaml inspect  # just scan channels/rows per file
python -m hyperscanning_toolkit --config config.yaml extract  # just apply epoching, write cleaned CSVs
python -m hyperscanning_toolkit --config config.yaml graphs   # just build graphs from cleaned CSVs
python -m hyperscanning_toolkit --version                     # print the installed toolkit version
```

Every run prints its version banner first and ends with a run summary
(sessions discovered/processed/skipped, participant files, graphs built,
failed correlations, all-NaN files, constant channels, duplicate subjects
skipped, total runtime). Every individual graph's output folder also gets a
`run_metadata.json` — toolkit version, git commit, timestamp, the exact
command and config file used, the connectivity method and thresholds, the
channels tested, and the Python/numpy/scipy/networkx/pandas versions — so any
single graph's folder is self-describing for reproducibility even in
isolation.

Pointing the toolkit at a new dataset means writing a new `config.yaml` —
no source changes. See `hyperscanning_toolkit/config.py` for the full schema;
in short:

```yaml
channels:
  mode: auto            # "auto" (all numeric cols) | "regex" | "explicit"
  # pattern: "^EEG_.*$"
  # columns: [ch1, ch2]
  exclude: []            # numeric columns to skip in "auto" mode

epoching:
  mode: none             # "none" | "fixed_window" | "event_marker"
  # window_size: 100
  # start_column: StartEvent
  # end_column: EndEvent
  # start_pattern: "^EPOCH(\\d+)$"
  # end_pattern: "^EPOCH(\\d+)_END$"

discovery:
  root: data
  session_glob: "*/dyad_*/session_*"   # one glob match = one recording session
  level_names: [condition, dyad, session]  # labels for each path segment matched above
  file_glob: "subject_*.xlsx"
  filename_subject_regex: "subject_(\\d+)"

thresholds:
  p_threshold: 0.05
  r_threshold: 0.0

output_dir: outputs
```

## Input and output overview

**Input:** one CSV/XLSX file per participant per session, containing a time
column-free table of numeric signal channels (plus, optionally, epoch/event
marker columns) — see the `config.yaml` schema above for how a dataset's
folder layout, channel columns, and epoching scheme are described without
touching any code.

**Output**, written under `output_dir`:
- `channel_inspection/valid_channels_all_sessions.csv` — one row per file scanned.
- `cleaned_epochs/*.csv` — one epoched CSV per participant/session, plus `epoch_summary.csv`.
- `graphs/{inter,intra}/.../` — per-graph `adjacency_matrix.csv`, `edge_table.csv`,
  `all_tested_edges.csv`, `graph_metrics.csv`, `node_metrics.csv`, `graph.png`,
  and `run_metadata.json`, plus dataset-wide `graphs/{inter,intra}_graph_summary.csv`.

## Pipeline stages

1. **inspect** — scans `discovery.root` for session folders/participant files
   and reports channel counts per file
   (`outputs/channel_inspection/valid_channels_all_sessions.csv`).
2. **extract** — applies the configured epoching strategy per file and writes
   cleaned CSVs (`outputs/cleaned_epochs/`).
3. **graphs** — computes Pearson-correlation connectivity between every pair
   of channels (within a participant for intra-brain, across each pair of
   participants in a session for inter-brain), thresholds by
   `p_threshold`/`r_threshold`, and writes adjacency matrices, edge tables,
   node/graph-level metrics (degree, centrality, density, clustering,
   modularity, global efficiency, ...) and a graph visualization per
   participant/pair, plus `outputs/graphs/{inter,intra}_graph_summary.csv`
   across the whole dataset.

## Package layout

```
hyperscanning_toolkit/
├── _version.py        # single source of truth for the version string
├── config.py           # YAML config schema
├── discovery.py         # generic file discovery + cleaned-filename encoding + duplicate-subject detection
├── channels.py          # channel/column selection
├── epoching.py           # epoch-extraction strategies
├── connectivity.py       # Pearson correlation + significance thresholding
├── graphs.py              # graph construction, metrics, visualization
├── diagnostics.py         # constant-channel / all-NaN-file detection (reporting only, no math change)
├── run_summary.py         # aggregate run counters + human-readable summary
├── metadata.py             # run_metadata.json generation (versions, environment, config, timestamps)
├── pipeline.py             # orchestration (inspect / extract / graphs / run)
└── cli.py                  # `python -m hyperscanning_toolkit`
```

## Tests

```bash
python -m pytest tests/
```

`tests/test_pipeline.py` runs the full pipeline against a synthetic dataset
with made-up column names and epoch markers, to confirm the toolkit isn't
secretly fNIRS-specific.

## Status

Implemented: config-driven channel selection, pluggable epoching, generic
file discovery, inter/intra-brain graph construction with node/graph metrics
and visualization, CLI.

Planned: pluggable connectivity metrics beyond Pearson correlation (coherence,
wavelet transform coherence, mutual information); N-participant hyperbrain
graphs (currently pairwise-only); statistical group comparisons.

## Citation

If you use this software, please cite it using the metadata in
[`CITATION.cff`](CITATION.cff) (GitHub renders a "Cite this repository"
button from this file automatically). At minimum:

```
Moshe, Y. H. (2026). Hyperscanning Toolkit (Version 1.0.0) [Computer software].
https://github.com/YaelMoshe/hyperscanning-toolkit
```

## Development and attribution

### Lead Developer

**Dr. Yael Hodaya Moshe**

Responsible for the software architecture, pipeline design, Python
implementation, testing, documentation, releases, and maintenance of the
toolkit.

### Scientific Supervision

- Dr. Hila Gvirts
- Dr. Anat Dahan

Developed in collaboration with the Social Neuroscience Lab as part of an
academic research collaboration.

See [`AUTHORS.md`](AUTHORS.md) for the full contributor list.

## License

A license has not yet been finalized for this repository. All rights are
reserved by the copyright holder until a license is chosen and added here.
Do not treat the absence of a license as permission to use, copy, modify, or
redistribute this code.
