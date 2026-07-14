#!/usr/bin/env python3
"""
Hyperscanning Toolkit

Copyright (c) 2026 Dr. Yael Hodaya Moshe.

Lead Developer:
    Dr. Yael Hodaya Moshe

Developed in collaboration with the Social Neuroscience Lab.

Scientific Supervision:
    Dr. Hila Gvirts
    Dr. Anat Dahan

This file is part of the Hyperscanning Toolkit.

---

Reshape the 3HYPER mother-infant fNIRS preprocessed .mat files into the
generic toolkit's expected dyad/condition/participant CSV layout.

Source variables are named `<Prefix><ID>_<Chromophore><Condition>`, e.g.
`Baby040_HbOE`, `MOM0100_HbRI`, `Mother059_HbOF` — see
3HYPER_Dataset_Documentation.md for the full naming scheme. This script:

  - reads all four .mat files (the two main HbO+HbR files, plus the two
    supplementary HbR-only files that fill in HbR for later-batch subjects),
  - merges every (role, dyad, condition) record's HbO/HbR arrays regardless
    of which file they came from,
  - normalizes dyad IDs to plain integers so "0100" and "100" collapse to
    the same dyad,
  - accepts both "MOM" and "Mother" as the mother-role prefix,
  - writes one CSV per dyad/condition/role with columns
    HbO_CH1..HbO_CH18, HbR_CH1..HbR_CH18 (only the chromophores actually
    present for that record; a dyad missing HbR simply gets HbO-only columns),
  - prints a validation report of what was found and what's missing.

Usage:
    python reshape_mat_to_csv.py \\
        --baby-hbo-hbr "<path to baby_HBO_HBR.mat>" \\
        --mom-hbo-hbr "<path to MOM_HBO_HBR.mat>" \\
        --baby-hbr-condition "<path to Baby_HBR_condition.mat>" \\
        --mom-hbr-condition "<path to MOM_HBR_condition.mat>" \\
        [--output-dir <path, default: ../../data next to this script>] \\
        [--report <path, default: ../../outputs/3hyper_reshape_report.md>]
"""

import argparse
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd
import scipy.io as sio

VAR_RE = re.compile(r"^(Baby|MOM|Mother)(\d+)_(HbO|HbR)(E|F|I)$")
ROLE_BY_PREFIX = {"Baby": "baby", "MOM": "mom", "Mother": "mom"}
CHROMOPHORES = ("HbO", "HbR")
CONDITIONS = ("E", "F", "I")
N_CHANNELS = 18

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / ".." / ".." / "data"
DEFAULT_REPORT_PATH = Path(__file__).resolve().parent / ".." / ".." / "outputs" / "3hyper_mother_infant" / "3hyper_reshape_report.md"


def load_mat_variables(path: Path) -> dict:
    """Load a .mat file's top-level variables, excluding MATLAB bookkeeping keys."""
    data = sio.loadmat(path)
    return {k: v for k, v in data.items() if not k.startswith("__")}


def parse_variable_name(name: str):
    """Parse `<Prefix><ID>_<Chromophore><Condition>` -> (role, dyad_id:int, chrom, cond) or None."""
    m = VAR_RE.match(name)
    if not m:
        return None
    prefix, id_str, chrom, cond = m.groups()
    role = ROLE_BY_PREFIX.get(prefix)
    if role is None:
        return None
    return role, int(id_str), chrom, cond


def collect_records(mat_paths, warnings):
    """
    Read every .mat file and merge into:
        records[(role, dyad_id, cond)][chrom] = ndarray (samples x 18)
    Complementary files (main HbO+HbR vs. supplementary HbR-only) are merged
    by key; a genuine duplicate (same role/dyad/cond/chrom seen twice) is
    kept as first-seen and reported as a warning rather than silently
    overwritten.
    """
    records = defaultdict(dict)
    for path in mat_paths:
        variables = load_mat_variables(path)
        for name, arr in variables.items():
            parsed = parse_variable_name(name)
            if parsed is None:
                warnings.append(f"{path.name}: unrecognized variable name {name!r}, skipped")
                continue
            role, dyad_id, chrom, cond = parsed

            if arr.ndim != 2 or arr.shape[1] != N_CHANNELS:
                warnings.append(f"{path.name}: {name!r} has unexpected shape {arr.shape}, skipped")
                continue

            key = (role, dyad_id, cond)
            if chrom in records[key]:
                warnings.append(
                    f"{path.name}: duplicate {role}/dyad {dyad_id}/{cond}/{chrom} "
                    f"(variable {name!r}) — keeping the first one seen"
                )
                continue
            records[key][chrom] = arr

    return records


def write_csvs(records, output_root: Path, warnings):
    """Write one CSV per (role, dyad_id, cond) with HbO_CH1..18 / HbR_CH1..18 columns."""
    written = []

    for (role, dyad_id, cond), chroms in sorted(records.items()):
        columns = {}
        lengths = set()
        for chrom in CHROMOPHORES:
            if chrom not in chroms:
                continue
            arr = chroms[chrom]
            lengths.add(arr.shape[0])
            for ch in range(N_CHANNELS):
                columns[f"{chrom}_CH{ch + 1}"] = arr[:, ch]

        if not columns:
            continue

        n_samples = min(lengths)
        if len(lengths) > 1:
            warnings.append(
                f"dyad {dyad_id}/{role}/{cond}: HbO/HbR sample counts differ {sorted(lengths)}, "
                f"truncated to {n_samples}"
            )

        ordered_cols = [f"HbO_CH{i + 1}" for i in range(N_CHANNELS) if f"HbO_CH{i + 1}" in columns]
        ordered_cols += [f"HbR_CH{i + 1}" for i in range(N_CHANNELS) if f"HbR_CH{i + 1}" in columns]
        df = pd.DataFrame({c: columns[c][:n_samples] for c in ordered_cols})

        out_dir = output_root / f"dyad_{dyad_id}" / f"condition_{cond}"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"subject_{role}.csv"
        df.to_csv(out_path, index=False)

        written.append({
            "dyad": dyad_id,
            "condition": cond,
            "role": role,
            "path": out_path,
            "n_rows": len(df),
            "chromophores": sorted(chroms.keys()),
        })

    return written


def build_validation_report(records, written, warnings):
    all_dyads = sorted({dyad_id for (_role, dyad_id, _cond) in records.keys()})

    conditions_present = defaultdict(set)          # (dyad, role) -> {cond, ...}
    chroms_present = defaultdict(set)               # (dyad, role, cond) -> {chrom, ...}
    for (role, dyad_id, cond), chroms in records.items():
        conditions_present[(dyad_id, role)].add(cond)
        chroms_present[(dyad_id, role, cond)] = set(chroms.keys())

    matched_pairs = []
    missing_participants = []
    for dyad_id in all_dyads:
        has_baby = (dyad_id, "baby") in conditions_present
        has_mom = (dyad_id, "mom") in conditions_present
        if has_baby and has_mom:
            matched_pairs.append(dyad_id)
        else:
            missing_participants.append({
                "dyad": dyad_id,
                "missing_role": "mom" if has_baby else "baby",
            })

    missing_conditions = []
    for (dyad_id, role), conds in sorted(conditions_present.items()):
        missing = sorted(set(CONDITIONS) - conds)
        if missing:
            missing_conditions.append({"dyad": dyad_id, "role": role, "missing_conditions": missing})

    missing_chromophores = []
    for (dyad_id, role, cond), chroms in sorted(chroms_present.items()):
        missing = sorted(set(CHROMOPHORES) - chroms)
        if missing:
            missing_chromophores.append({
                "dyad": dyad_id, "role": role, "condition": cond, "missing_chromophores": missing,
            })

    return {
        "dyads": all_dyads,
        "matched_pairs": matched_pairs,
        "missing_participants": missing_participants,
        "missing_conditions": missing_conditions,
        "missing_chromophores": missing_chromophores,
        "output_files": written,
        "warnings": warnings,
    }


def render_report(report: dict) -> str:
    lines = []
    lines.append("# 3HYPER reshape validation report")
    lines.append("")
    lines.append(f"Discovered dyads: {len(report['dyads'])} — {report['dyads']}")
    lines.append("")
    lines.append(f"Matched mother-baby pairs: {len(report['matched_pairs'])} — {report['matched_pairs']}")
    lines.append("")
    lines.append(f"Missing participants ({len(report['missing_participants'])}):")
    for row in report["missing_participants"]:
        lines.append(f"  - dyad {row['dyad']}: no {row['missing_role']} data at all")
    lines.append("")
    lines.append(f"Dyads/roles missing one or more conditions ({len(report['missing_conditions'])}):")
    for row in report["missing_conditions"]:
        lines.append(f"  - dyad {row['dyad']} / {row['role']}: missing {row['missing_conditions']}")
    lines.append("")
    lines.append(f"Dyad/role/condition records missing a chromophore ({len(report['missing_chromophores'])}):")
    for row in report["missing_chromophores"]:
        lines.append(
            f"  - dyad {row['dyad']} / {row['role']} / {row['condition']}: "
            f"missing {row['missing_chromophores']}"
        )
    lines.append("")
    lines.append(f"Output files written: {len(report['output_files'])}")
    for row in report["output_files"]:
        lines.append(
            f"  - {row['path']}  (dyad {row['dyad']}, {row['role']}, {row['condition']}, "
            f"{row['n_rows']} rows, chromophores={row['chromophores']})"
        )
    if report["warnings"]:
        lines.append("")
        lines.append(f"Warnings ({len(report['warnings'])}):")
        for w in report["warnings"]:
            lines.append(f"  - {w}")
    lines.append("")
    return "\n".join(lines)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Reshape the 3HYPER mother-infant .mat files into per-dyad/condition/role CSVs."
    )
    parser.add_argument("--baby-hbo-hbr", required=True, help="Path to baby_HBO_HBR.mat")
    parser.add_argument("--mom-hbo-hbr", required=True, help="Path to MOM_HBO_HBR.mat")
    parser.add_argument("--baby-hbr-condition", required=True, help="Path to Baby_HBR_condition.mat")
    parser.add_argument("--mom-hbr-condition", required=True, help="Path to MOM_HBR_condition.mat")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"Where to write the reshaped CSV tree (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--report",
        default=str(DEFAULT_REPORT_PATH),
        help=f"Where to write the validation report (default: {DEFAULT_REPORT_PATH})",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    mat_paths = [
        Path(args.baby_hbo_hbr),
        Path(args.mom_hbo_hbr),
        Path(args.baby_hbr_condition),
        Path(args.mom_hbr_condition),
    ]
    for p in mat_paths:
        if not p.exists():
            raise FileNotFoundError(f"Input .mat file not found: {p}")

    output_root = Path(args.output_dir)
    report_path = Path(args.report)

    warnings = []
    records = collect_records(mat_paths, warnings)
    written = write_csvs(records, output_root, warnings)
    report = build_validation_report(records, written, warnings)
    report_text = render_report(report)

    print(report_text)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text, encoding="utf-8")
    print(f"Saved report: {report_path}")


if __name__ == "__main__":
    main()
