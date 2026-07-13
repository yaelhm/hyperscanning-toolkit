# Hyperscanning Toolkit

A config-driven pipeline for building inter-brain (dyadic) and intra-brain
functional connectivity graphs from hyperscanning timeseries data. The core
package makes no assumptions about signal modality (fNIRS, EEG, ECG, GSR, ...),
epoch/marker scheme, or folder layout — every dataset-specific detail lives in
one YAML config file.

See [`examples/fnirs_neurofeedback_lab/`](examples/fnirs_neurofeedback_lab/)
for a full worked example (this lab's fNIRS neurofeedback study) including
the config that reproduces it.

## Install

```bash
pip install -e .
```

## Usage

```bash
python -m hyperscanning_toolkit --config config.yaml run     # inspect -> extract -> graphs
python -m hyperscanning_toolkit --config config.yaml inspect  # just scan channels/rows per file
python -m hyperscanning_toolkit --config config.yaml extract  # just apply epoching, write cleaned CSVs
python -m hyperscanning_toolkit --config config.yaml graphs   # just build graphs from cleaned CSVs
```

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
├── config.py         # YAML config schema
├── discovery.py       # generic file discovery + cleaned-filename encoding
├── channels.py        # channel/column selection
├── epoching.py         # epoch-extraction strategies
├── connectivity.py     # Pearson correlation + significance thresholding
├── graphs.py            # graph construction, metrics, visualization
├── pipeline.py           # orchestration (inspect / extract / graphs / run)
└── cli.py                # `python -m hyperscanning_toolkit`
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
