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

Reorganize fNIRS dataset from flat structure to hierarchical dyad/session structure.

Input:
  <nfb-dir>/*.xlsx
  <control-dir>/*.xlsx

Output:
  <output-dir>/
  ├── NFB/
  │   └── dyad_XXXX/
  │       └── session_XX/
  │           ├── subject_01.xlsx
  │           └── subject_02.xlsx
  ├── Control/
  │   └── dyad_XXXX/
  │       └── session_XX/
  │           ├── subject_01.xlsx
  │           └── subject_02.xlsx
  ├── summary.csv
  └── dyad_manifest.csv

Usage:
    python reorganize_dataset.py \\
        --nfb-dir "<path to NFB O2HB Data>" \\
        --control-dir "<path to Control O2HB Data>" \\
        [--output-dir <path, default: ../../data next to this script>]
"""

import argparse
import csv
import shutil
from collections import defaultdict
from pathlib import Path

import openpyxl

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / ".." / ".." / "data"

# Configuration, set from CLI args in main()
SOURCE_DIRS = {}
OUTPUT_BASE = None

# Data structures for tracking
summary_data = []
dyad_manifest = []
warnings_list = []
processed_files = {}
dyad_sessions = defaultdict(lambda: defaultdict(dict))


def log_warning(msg):
    """Log a warning message"""
    warnings_list.append(msg)
    print(f"  ⚠ WARNING: {msg}")


def extract_metadata(filepath):
    """Extract Group, Session, Subject from Excel file (optimized for speed)"""
    try:
        # Use read_only mode to read just the first 2 rows quickly
        wb = openpyxl.load_workbook(filepath, data_only=True, read_only=True)
        ws = wb.active

        # Read only first 2 rows
        rows = []
        for i, row in enumerate(ws.iter_rows(values_only=True), 1):
            rows.append(row)
            if i >= 2:  # Only need first 2 rows
                break

        wb.close()

        if len(rows) < 2:
            log_warning(f"{filepath.name} - Insufficient data (< 2 rows)")
            return None

        headers = rows[0]
        data_row = rows[1]

        if headers is None or data_row is None:
            log_warning(f"{filepath.name} - Empty rows")
            return None

        if 'Group' not in headers or 'Session' not in headers or 'Subject' not in headers:
            log_warning(f"{filepath.name} - Missing required headers")
            return None

        try:
            group = int(data_row[headers.index('Group')])
            session = int(data_row[headers.index('Session')])
            subject = int(data_row[headers.index('Subject')])
        except (ValueError, TypeError, IndexError) as e:
            log_warning(f"{filepath.name} - Error parsing metadata: {e}")
            return None

        return {'group': group, 'session': session, 'subject': subject}

    except Exception as e:
        log_warning(f"{filepath.name} - Failed to read: {e}")
        return None


def reorganize_files(condition, source_dir):
    """Reorganize files for a given condition (NFB or Control)"""
    print(f"\n{'='*80}")
    print(f"Processing {condition} files...")
    print(f"{'='*80}")

    if not source_dir.exists():
        print(f"ERROR: Source directory not found: {source_dir}")
        return

    # Get all Excel files
    excel_files = sorted(source_dir.glob("*.xlsx"))
    print(f"Found {len(excel_files)} files in {condition}\n")

    if len(excel_files) == 0:
        log_warning(f"No Excel files found in {source_dir}")
        return

    # Track files by dyad/session/subject
    dyad_files = defaultdict(lambda: defaultdict(dict))

    # Process each file
    for fpath in excel_files:
        metadata = extract_metadata(fpath)

        if metadata is None:
            continue

        group = metadata['group']
        session = metadata['session']
        subject = metadata['subject']

        # Validate subject (should be 1 or 2)
        if subject not in [1, 2]:
            log_warning(f"{fpath.name} - Invalid subject value: {subject}")
            continue

        # Store file information
        dyad_files[group][session][subject] = {
            'filename': fpath.name,
            'path': fpath,
            'subject': subject
        }

        print(f"✓ {fpath.name}")
        print(f"  → Group {group}, Session {session}, Subject {subject}")

    # Create output directories and copy files
    print(f"\n{'='*80}")
    print(f"Creating directory structure and copying files...")
    print(f"{'='*80}\n")

    output_condition_dir = OUTPUT_BASE / condition

    for group in sorted(dyad_files.keys()):
        dyad_id = f"{group:04d}"
        dyad_dir = output_condition_dir / f"dyad_{dyad_id}"

        for session in sorted(dyad_files[group].keys()):
            session_id = f"{session:02d}"
            session_dir = dyad_dir / f"session_{session_id}"
            session_dir.mkdir(parents=True, exist_ok=True)

            subjects_in_session = dyad_files[group][session]

            # Validate that we have both subjects
            if 1 not in subjects_in_session and 2 not in subjects_in_session:
                log_warning(f"Group {group} Session {session} - No subjects found")
                continue

            if len(subjects_in_session) < 2:
                missing_subject = 2 if 1 in subjects_in_session else 1
                log_warning(f"Group {group} Session {session} - Missing subject {missing_subject}")

            # Check for duplicate subjects
            for subject, file_info in subjects_in_session.items():
                if isinstance(file_info, dict) and 'path' in file_info:
                    # Single file
                    src_path = file_info['path']
                    dst_filename = f"subject_{subject:02d}.xlsx"
                    dst_path = session_dir / dst_filename

                    # Copy file
                    shutil.copy2(src_path, dst_path)
                    print(f"  ✓ {condition}/dyad_{dyad_id}/session_{session_id}/{dst_filename}")

                    # Record for summary
                    processed_files[str(src_path)] = {
                        'condition': condition,
                        'dyad_id': dyad_id,
                        'session': session_id,
                        'subject': subject,
                        'src': src_path.name,
                        'dst': str(dst_path.relative_to(OUTPUT_BASE))
                    }

                    summary_data.append({
                        'condition': condition,
                        'dyad_id': dyad_id,
                        'session': session_id,
                        'subject': subject,
                        'original_filename': src_path.name,
                        'new_filepath': str(dst_path.relative_to(OUTPUT_BASE))
                    })

            # Add to dyad manifest
            subject_1_file = f"subject_01.xlsx" if 1 in subjects_in_session else "MISSING"
            subject_2_file = f"subject_02.xlsx" if 2 in subjects_in_session else "MISSING"

            dyad_manifest.append({
                'condition': condition,
                'dyad_id': dyad_id,
                'session': session_id,
                'subject1_file': subject_1_file,
                'subject2_file': subject_2_file
            })


def generate_reports():
    """Generate summary and manifest CSV files"""
    print(f"\n{'='*80}")
    print("Generating CSV reports...")
    print(f"{'='*80}\n")

    # Write summary.csv
    summary_path = OUTPUT_BASE / "summary.csv"
    with open(summary_path, 'w', newline='', encoding='utf-8') as f:
        if summary_data:
            fieldnames = list(summary_data[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(summary_data)
    print(f"✓ Generated: {summary_path.name} ({len(summary_data)} records)")

    # Write dyad_manifest.csv
    manifest_path = OUTPUT_BASE / "dyad_manifest.csv"
    with open(manifest_path, 'w', newline='', encoding='utf-8') as f:
        if dyad_manifest:
            fieldnames = list(dyad_manifest[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(dyad_manifest)
    print(f"✓ Generated: {manifest_path.name} ({len(dyad_manifest)} records)")


def print_summary():
    """Print summary statistics"""
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}\n")

    print(f"Files processed: {len(processed_files)}")
    print(f"Summary records: {len(summary_data)}")
    print(f"Dyad-session combinations: {len(dyad_manifest)}")
    print(f"Warnings: {len(warnings_list)}")

    if warnings_list:
        print(f"\n{'='*80}")
        print("WARNINGS")
        print(f"{'='*80}\n")
        for i, warning in enumerate(warnings_list, 1):
            print(f"{i}. {warning}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Reorganize raw fNIRS Excel exports into a dyad/session folder structure."
    )
    parser.add_argument("--nfb-dir", required=True, help="Path to the raw 'NFB O2HB Data' folder")
    parser.add_argument("--control-dir", required=True, help="Path to the raw 'Control O2HB Data' folder")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"Where to write the reorganized dataset (default: {DEFAULT_OUTPUT_DIR})",
    )
    return parser.parse_args()


def main():
    """Main execution"""
    global SOURCE_DIRS, OUTPUT_BASE

    args = parse_args()
    SOURCE_DIRS = {'NFB': Path(args.nfb_dir), 'Control': Path(args.control_dir)}
    OUTPUT_BASE = Path(args.output_dir)

    print(f"\n{'='*80}")
    print("FNIRS DATASET REORGANIZER")
    print(f"{'='*80}\n")

    # Create output directory
    OUTPUT_BASE.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {OUTPUT_BASE}\n")

    # Process both conditions
    for condition, source_dir in SOURCE_DIRS.items():
        reorganize_files(condition, source_dir)

    # Generate reports
    generate_reports()

    # Print summary
    print_summary()

    print(f"\n{'='*80}")
    print("✓ REORGANIZATION COMPLETE")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
