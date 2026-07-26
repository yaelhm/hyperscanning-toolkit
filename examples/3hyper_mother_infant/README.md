# Example: 3HYPER mother-infant fNIRS hyperscanning

Worked example of pointing the generic `hyperscanning_toolkit` package at the
3HYPER mother-infant dataset. Nothing in here is imported by the toolkit
itself; it exists to show how this dataset gets adapted.

See `3HYPER_Dataset_Documentation.md` (provided alongside the dataset, not
part of this repo) for the full description of the source files. Two things
in that documentation are worth calling out explicitly here because they
affect this adapter:

- **Two undocumented files.** Alongside the two files the documentation
  names (`baby_HBO_HBR.mat`, `MOM_HBO_HBR.mat`), the actual data drop also
  included `Baby_HBR_condition.mat` and `MOM_HBR_condition.mat`. These
  aren't mentioned in the documentation, but they exactly fill the HbR gaps
  in the two main files (no overlap, no duplication) — later-batch subjects
  are HbO-only in the main files and get their HbR from these two. The
  adapter reads all four; using only the two documented files would silently
  produce HbO-only data for most later-batch dyads.
- **Zero-padded IDs.** The mother file uses 4-digit IDs for some dyads
  (`MOM0100_...`) while the infant file uses 3-digit IDs for the same dyads
  (`Baby100_...`). The adapter normalizes every ID to a plain integer before
  building output paths, so `0100` and `100` collapse into the same
  `dyad_100` — otherwise those 3 dyads would silently split into two
  half-empty "dyads" each.

## 1. Reshape the .mat files into the toolkit's expected layout

```bash
python reshape_mat_to_csv.py \
    --baby-hbo-hbr "<path to baby_HBO_HBR.mat>" \
    --mom-hbo-hbr "<path to MOM_HBO_HBR.mat>" \
    --baby-hbr-condition "<path to Baby_HBR_condition.mat>" \
    --mom-hbr-condition "<path to MOM_HBR_condition.mat>"
```

This writes, by default, to `../../data`:

```
data/
└── dyad_<ID>/
    └── condition_<E|F|I>/
        ├── subject_baby.csv   # HbO_CH1..HbO_CH18, HbR_CH1..HbR_CH18 (whichever chromophores exist)
        └── subject_mom.csv
```

and prints + saves a validation report (default
`../../outputs/3hyper_mother_infant/3hyper_reshape_report.md`) listing
discovered dyads, matched mother-baby pairs, missing participants, missing
conditions, missing chromophores, and every file written.

Expect a handful of genuine gaps reflecting real data-collection issues
(not adapter bugs) — e.g. dyads with a session that was never fully
recorded end up missing the Elicited/Instructed condition for both roles.
Check the report rather than assuming full coverage.

## 2. Run the generic toolkit against the reshaped data

Everything dataset-specific lives in `config.yaml`: the `HbO_CH<N>` channel
regex, `epoching.mode: none` (the `.mat` arrays are already condition-segmented,
so there's nothing left to epoch), and the `dyad/condition` folder layout.

```bash
pip install -e ../..
python -m hyperscanning_toolkit --config config.yaml run
```

Swap the channel `pattern` to `^HbR_CH\d+$` to re-run the same reshaped CSVs
against HbR instead of HbO — no need to re-run the adapter.

## Known gap versus the full study design

The example input scenario for this dataset asks for two network levels:
each participant's intra-brain network and the mother-infant inter-brain
network. The toolkit as it stands today builds the first
two (intra-brain per participant, inter-brain per pair) but has no step that
merges them into a third combined hyper-brain graph, and no ROI-aggregation
step — node metrics are per-channel only. Both would be additive follow-up
work on the toolkit itself, not something this adapter can produce on its own.
