"""
Read input/consumables.csv (after lot_number and expiry are filled in)
and insert records into consumable_lots in research.db.
Rows with empty lot_number are skipped.

Usage:
    python3 scripts/insert_consumable_lots.py <project_id> <date> <experiment_name>

Arguments:
    project_id      : 1=MATRX, 2=small-genes, 3=diabetic-small-genes, 4=MitoPilot, 5=COMIT
    date            : YYYY-MM-DD (date the experiment was run)
    experiment_name : must match the name used in new_experiment.sh

Example:
    python3 scripts/insert_consumable_lots.py 3 2026-01-21 mito-rna-extraction
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


def nullable_str(val):
    return val.strip() or None


if len(sys.argv) < 4:
    print(__doc__)
    sys.exit(1)

project_id      = int(sys.argv[1])
date            = sys.argv[2]
experiment_name = sys.argv[3]

project_dir = PROJECT_DIRS.get(project_id)
if not project_dir:
    print(f"ERROR: unknown project_id {project_id}. Valid: {list(PROJECT_DIRS)}")
    sys.exit(1)

experiment_dir = Path("projects") / project_dir / "lab-notebook" / "experiments" / f"{date}_{experiment_name}"
csv_path       = experiment_dir / "input" / "consumables.csv"
pt_file        = experiment_dir / "input" / "procedure_type.txt"

if not csv_path.exists():
    print(f"ERROR: {csv_path} not found — run generate_consumables_template.py first")
    sys.exit(1)

procedure_label = pt_file.read_text().strip().replace("\n", ", ") if pt_file.exists() else experiment_name

db = sqlite3.connect("research.db")
db.row_factory = sqlite3.Row
db.execute("PRAGMA foreign_keys = ON")

# name → consumable_id
name_to_id = {
    row["name"]: row["consumable_id"]
    for row in db.execute("SELECT consumable_id, name FROM consumables")
}

rows = []
skipped = []

for row in csv.DictReader(open(csv_path)):
    name       = row["consumable"].strip()
    lot_number = nullable_str(row.get("lot_number", ""))
    expiry     = nullable_str(row.get("expiry", ""))

    if not lot_number:
        skipped.append(name)
        continue

    consumable_id = name_to_id.get(name)
    if not consumable_id:
        print(f"WARNING: consumable not found in DB: '{name}' — skipped")
        continue

    rows.append((
        consumable_id,
        lot_number,
        expiry,
        date,   # date_received = date used (experiment date)
        f"{date} {experiment_name} ({procedure_label})",  # notes
    ))

if skipped:
    print(f"Skipped (no lot number): {skipped}")

print(f"Inserting {len(rows)} lot records...")

with db:
    db.executemany("""
        INSERT INTO consumable_lots
            (consumable_id, lot_number, expiry, date_received, notes)
        VALUES (?,?,?,?,?)
    """, rows)

print("Done. Verifying...")
print()

for r in db.execute("""
    SELECT c.name, cl.lot_number, cl.expiry, cl.notes
    FROM consumable_lots cl
    JOIN consumables c ON c.consumable_id = cl.consumable_id
    WHERE cl.notes LIKE ?
    ORDER BY c.name
""", (f"{date} {experiment_name}%",)):
    print(f"  {r['name']:40}  lot={r['lot_number']}  expiry={r['expiry']}")

db.close()
