"""
Insert RNA extraction rows from a filled-in results/rna_extraction.csv into research.db.
sample_id is read directly from the CSV (pre-filled by generate_extraction_template.py).

Usage:
    python3 scripts/insert_rna_extractions.py <csv_path> <project_id>

CSV columns:
    mouse_id, sample_id, date, tissue (mito|wm),
    trizol_vol_ul, etoh_vol_ul, elution_vol_ul, dilution_factor, notes

Example:
    python3 scripts/insert_rna_extractions.py \\
        projects/diabetic-small-genes/lab-notebook/experiments/2026-01-21_mito-rna-extraction/results/rna_extraction.csv \\
        3
"""

import csv
import sqlite3
import sys
from pathlib import Path


def nullable_float_or_str(val):
    if not val or not val.strip():
        return None
    try:
        return float(val)
    except ValueError:
        return val.strip()

def nullable_str(val):
    return val.strip() or None


if len(sys.argv) < 3:
    print(__doc__)
    sys.exit(1)

csv_path   = Path(sys.argv[1])
project_id = int(sys.argv[2])

db = sqlite3.connect("research.db")
db.row_factory = sqlite3.Row
db.execute("PRAGMA foreign_keys = ON")

# mouse_id → anchor_id for this project
mouse_to_anchor = {
    row["mouse_id"]: row["anchor_id"]
    for row in db.execute("""
        SELECT m.mouse_id, a.anchor_id
        FROM mice m JOIN anchors a ON a.anchor_id = m.anchor_id
        WHERE a.project_id = ?
    """, (project_id,))
}

TISSUE_TYPE = {"mito": "gastrocnemius", "wm": "gastrocnemius"}

sample_rows     = []
extraction_rows = []
skipped         = []

for row in csv.DictReader(open(csv_path)):
    mid    = row["mouse_id"].strip()
    date   = row["date"].strip()
    tissue = row["tissue"].strip().lower()
    anchor_id = mouse_to_anchor.get(mid)

    if not anchor_id:
        skipped.append(mid)
        continue

    if tissue not in ("mito", "wm"):
        print(f"ERROR: unrecognised tissue '{tissue}' for {mid} — must be 'mito' or 'wm'")
        sys.exit(1)

    sample_id = row["sample_id"].strip()

    sample_rows.append((
        sample_id,
        anchor_id,
        TISSUE_TYPE[tissue],
        "rna_extract",
        date,
        None,   # amount
        None,   # unit
        None,   # notes
    ))

    extraction_rows.append((
        sample_id,
        date,
        nullable_float_or_str(row.get("trizol_vol_ul", "")),
        nullable_float_or_str(row.get("etoh_vol_ul", "")),
        nullable_float_or_str(row.get("elution_vol_ul", "")),
        nullable_float_or_str(row.get("dilution_factor", "")),
        nullable_str(row.get("notes", "")),
    ))

if skipped:
    print(f"WARNING: no anchor found for: {skipped}")

print(f"Inserting {len(sample_rows)} samples and {len(extraction_rows)} extraction rows...")

with db:
    db.executemany("""
        INSERT OR IGNORE INTO samples
            (sample_id, anchor_id, tissue_type, sample_type, date, amount, unit, notes)
        VALUES (?,?,?,?,?,?,?,?)
    """, sample_rows)

    db.executemany("""
        INSERT OR IGNORE INTO rna_extractions
            (sample_id, date, trizol_vol_ul, etoh_vol_ul, elution_vol_ul, dilution_factor, notes)
        VALUES (?,?,?,?,?,?,?)
    """, extraction_rows)

print("Done. Verifying...")
print()

for r in db.execute("""
    SELECT m.mouse_id, s.sample_id, e.date, e.trizol_vol_ul, e.elution_vol_ul
    FROM rna_extractions e
    JOIN samples s ON s.sample_id = e.sample_id
    JOIN anchors a ON a.anchor_id = s.anchor_id
    JOIN mice m    ON m.anchor_id = a.anchor_id
    WHERE a.project_id = ?
      AND e.sample_id IN ({})
    ORDER BY m.mouse_id
""".format(",".join("?" * len(extraction_rows))),
    [project_id] + [r[0] for r in extraction_rows]
):
    print(f"  {r['mouse_id']:8}  {r['sample_id']}  trizol={r['trizol_vol_ul']}ul  elution={r['elution_vol_ul']}ul")

db.close()
