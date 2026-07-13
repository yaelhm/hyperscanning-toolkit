#!/usr/bin/env python3
"""
Inspect metadata from Excel files to understand the data structure.
This script analyzes Group, Session, and Subject metadata before reorganizing.

Usage:
    python inspect_metadata.py --nfb-dir "<path to NFB O2HB Data>" --control-dir "<path to Control O2HB Data>"
"""

import argparse
from collections import defaultdict
from pathlib import Path

import openpyxl


def extract_metadata_from_file(filepath):
    """Extract Group, Session, Subject from first data row of Excel file."""
    try:
        wb = openpyxl.load_workbook(filepath, data_only=True)
        ws = wb.active

        # Get headers from row 1
        headers = [cell.value for cell in ws[1]]

        if 'Group' not in headers or 'Session' not in headers or 'Subject' not in headers:
            print(f"  WARNING: Missing expected headers in {filepath.name}")
            return None

        # Get first data row (row 2)
        data_row = [cell.value for cell in ws[2]]

        group_idx = headers.index('Group')
        session_idx = headers.index('Session')
        subject_idx = headers.index('Subject')

        group = data_row[group_idx]
        session = data_row[session_idx]
        subject = data_row[subject_idx]

        wb.close()

        return {
            'group': group,
            'session': session,
            'subject': subject,
            'filename': filepath.name
        }
    except Exception as e:
        print(f"  ERROR reading {filepath.name}: {e}")
        return None


def inspect(nfb_dir: Path, control_dir: Path):
    # Collect metadata from all files
    print("=" * 80)
    print("SCANNING NFB FILES")
    print("=" * 80)

    nfb_metadata = defaultdict(list)
    nfb_files = sorted(nfb_dir.glob("*.xlsx"))[:10]  # First 10 files
    print(f"Scanning {len(nfb_files)} NFB files...\n")

    for fpath in nfb_files:
        meta = extract_metadata_from_file(fpath)
        if meta:
            nfb_metadata[(meta['group'], meta['session'])].append(meta)
            print(f"✓ {fpath.name}")
            print(f"  Group={meta['group']}, Session={meta['session']}, Subject={meta['subject']}")

    print(f"\n{'='*80}")
    print("SCANNING CONTROL FILES")
    print("=" * 80)

    control_metadata = defaultdict(list)
    control_files = sorted(control_dir.glob("*.xlsx"))[:10]  # First 10 files
    print(f"Scanning {len(control_files)} Control files...\n")

    for fpath in control_files:
        meta = extract_metadata_from_file(fpath)
        if meta:
            control_metadata[(meta['group'], meta['session'])].append(meta)
            print(f"✓ {fpath.name}")
            print(f"  Group={meta['group']}, Session={meta['session']}, Subject={meta['subject']}")

    print(f"\n{'='*80}")
    print("DETECTED METADATA STRUCTURE - NFB")
    print("=" * 80)
    print("\nGroup-Session combinations and their files:\n")

    for (group, session), files in sorted(nfb_metadata.items()):
        subjects = [f['subject'] for f in files]
        print(f"Group={group}, Session={session}")
        print(f"  Files: {len(files)}")
        print(f"  Subjects: {sorted(set(subjects))}")
        for f in files:
            print(f"    - {f['filename']} (Subject {f['subject']})")
        print()

    print(f"{'='*80}")
    print("DETECTED METADATA STRUCTURE - CONTROL")
    print("=" * 80)
    print("\nGroup-Session combinations and their files:\n")

    for (group, session), files in sorted(control_metadata.items()):
        subjects = [f['subject'] for f in files]
        print(f"Group={group}, Session={session}")
        print(f"  Files: {len(files)}")
        print(f"  Subjects: {sorted(set(subjects))}")
        for f in files:
            print(f"    - {f['filename']} (Subject {f['subject']})")
        print()

    print(f"{'='*80}")
    print("UNIQUE VALUES IN DATASET")
    print("=" * 80)

    all_nfb_groups = {g for (g, s) in nfb_metadata.keys()}
    all_nfb_sessions = {s for (g, s) in nfb_metadata.keys()}
    all_control_groups = {g for (g, s) in control_metadata.keys()}
    all_control_sessions = {s for (g, s) in control_metadata.keys()}

    print(f"\nNFB Groups: {sorted(all_nfb_groups)}")
    print(f"NFB Sessions: {sorted(all_nfb_sessions)}")
    print(f"Control Groups: {sorted(all_control_groups)}")
    print(f"Control Sessions: {sorted(all_control_sessions)}")

    print("\n" + "=" * 80)
    print("EXPECTED FOLDER STRUCTURE")
    print("=" * 80)
    print("""
data/
├── NFB/
│   ├── dyad_XXXX/
│   │   ├── session_01/
│   │   │   ├── subject_01.xlsx
│   │   │   └── subject_02.xlsx
│   │   ├── session_02/
│   │   │   ├── subject_01.xlsx
│   │   │   └── subject_02.xlsx
│   │   └── ...
│   └── ...
└── Control/
    ├── dyad_XXXX/
    │   ├── session_01/
    │   │   ├── subject_01.xlsx
    │   │   └── subject_02.xlsx
    │   ├── session_02/
    │   │   ├── subject_01.xlsx
    │   │   └── subject_02.xlsx
    │   └── ...
    └── ...

CSV Reports:
  - summary.csv
  - dyad_manifest.csv
""")


def main():
    parser = argparse.ArgumentParser(
        description="Inspect Group/Session/Subject metadata in raw fNIRS Excel exports."
    )
    parser.add_argument("--nfb-dir", required=True, help="Path to the raw 'NFB O2HB Data' folder")
    parser.add_argument("--control-dir", required=True, help="Path to the raw 'Control O2HB Data' folder")
    args = parser.parse_args()

    inspect(Path(args.nfb_dir), Path(args.control_dir))


if __name__ == "__main__":
    main()
