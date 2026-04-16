"""
Insert RNA QC rows from results/rna_qc.csv into research.db.
sample_id is read directly from the CSV (pre-filled by generate_qc_template.py).

Usage:
    python3 scripts/insert_rna_qc.py <project_id> <date> <experiment_name> <instrument> <tissue>

Arguments:
    project_id      : 1=MATRX, 2=small-genes, 3=diabetic-small-genes, 4=MitoPilot, 5=COMIT
    date            : YYYY-MM-DD (date QC was run)
    experiment_name : must match the name used in new_experiment.sh
    instrument      : tapestation | nanodrop
    tissue          : mito | wm

Example:
    python3 scripts/insert_rna_qc.py 3 2026-01-29 rna-qc-tapestation tapestation mito
"""

import csv
import sqlite3
import sys
from pathlib import Path

PROJECT_DIRS = {
    1: "MATRX-study",
    2: "small-genes-with-big-potential",
    3: "diabetic-small-genes",
    4: "MitoPilot",
    5: "COMIT",
}


def nullable_float(val):
    return float(val) if val and val.strip() else None

def nullable_str(val):
    return val.strip() or None


if len(sys.argv) < 6:
    print(__doc__)
    sys.exit(1)

project_id      = int(sys.argv[1])
date            = sys.argv[2]
experiment_name = sys.argv[3]
instrument      = sys.argv[4]
tissue          = sys.argv[5].lower()

if tissue not in ("mito", "wm"):
    print("ERROR: tissue must be 'mito' or 'wm'")
    sys.exit(1)

project_dir = PROJECT_DIRS.get(project_id)
if not project_dir:
    print(f"ERROR: unknown project_id {project_id}. Valid: {list(PROJECT_DIRS)}")
    sys.exit(1)

experiment_dir = Path("projects") / project_dir / "lab-notebook" / "experiments" / f"{date}_{experiment_name}"
csv_path = experiment_dir / "results" / "rna_qc.csv"

if not csv_path.exists():
    print(f"ERROR: {csv_path} not found — run generate_qc_template.py first")
    sys.exit(1)

db = sqlite3.connect("research.db")
db.row_factory = sqlite3.Row
db.execute("PRAGMA foreign_keys = ON")

rows = []
skipped = []
for row in csv.DictReader(open(csv_path)):
    sid = nullable_str(row.get("sample_id", ""))
    if not sid:
        skipped.append(row.get("mouse_id", "?"))
        continue
    rows.append((
        sid,
        date,
        instrument,
        nullable_str(row.get("well", "")),
        nullable_float(row.get("rin", "")),
        nullable_float(row.get("ratio_28s_18s", "")),
        nullable_float(row.get("concentration", "")),
        nullable_str(row.get("concentration_unit", "")),
        nullable_float(row.get("a260_280", "")),
        nullable_float(row.get("a260_230", "")),
        nullable_str(row.get("notes", "")),
    ))

if skipped:
    print(f"WARNING: no sample_id for: {skipped} — rows skipped")

print(f"Inserting {len(rows)} rows...")

with db:
    db.executemany("""
        INSERT INTO rna_qc
            (sample_id, date, instrument, well, rin, ratio_28s_18s,
             concentration, concentration_unit, a260_280, a260_230, notes)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, rows)

print("Done. Verifying...")
print()

for r in db.execute("""
    SELECT m.mouse_id, q.well, q.rin, q.concentration, q.concentration_unit
    FROM rna_qc q
    JOIN samples s ON s.sample_id = q.sample_id
    JOIN anchors a ON a.anchor_id = s.anchor_id
    JOIN mice m    ON m.anchor_id = a.anchor_id
    WHERE a.project_id = ? AND q.date = ?
    ORDER BY q.well
""", (project_id, date)):
    print(f"  {r['mouse_id']:8}  well={str(r['well']):4}  RIN={r['rin']}  conc={r['concentration']} {r['concentration_unit']}")

db.close()
