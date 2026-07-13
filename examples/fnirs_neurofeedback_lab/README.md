# Example: fNIRS neurofeedback hyperscanning lab

This is a worked example of pointing the generic `hyperscanning_toolkit`
package at one specific dataset — this lab's fNIRS hyperscanning
neurofeedback study. Nothing in here is imported by the toolkit itself;
it exists to show how a new dataset gets adapted.

## 1. Reshape the raw export (one-off, lab-specific)

The lab's raw Excel exports don't follow any folder convention the toolkit
understands, so `reorganize_dataset.py` copies them into
`dyad_XXXX/session_XX/subject_0{1,2}.xlsx` first (reading `Group`/`Session`/
`Subject` out of each file's data row):

```bash
python reorganize_dataset.py --nfb-dir "<path to NFB O2HB Data>" --control-dir "<path to Control O2HB Data>"
# writes to ../../data by default; override with --output-dir

python test_reorganize.py --nfb-dir "<path to NFB O2HB Data>" --control-dir "<path to Control O2HB Data>"
# smoke test: first 10 files per condition -> ../../data_test by default
```

`--nfb-dir`/`--control-dir` point at wherever the lab's raw Excel exports live
on your machine — there's no default, since that location is specific to
each researcher's setup and shouldn't be hardcoded into the script.

`inspect_metadata.py` is a read-only scan of the raw export used to sanity
check the Group/Session/Subject values before reorganizing.

## 2. Run the generic toolkit against the reshaped data

Everything dataset-specific from here on lives in `config.yaml`: the fNIRS
`Tx<N>_Rx<M>` channel regex, the `NFB<N>` / `NFB<N>_End` epoch markers, and
the `condition/dyad/session` folder layout.

```bash
pip install -e ../..
python -m hyperscanning_toolkit --config config.yaml run
```

This runs `inspect` -> `extract` -> `graphs` and writes everything under
`../../outputs/`. Porting this pipeline to a different dataset (different
signal type, different epoch scheme, different folder layout) means writing
a new `config.yaml` like this one — no code changes.
