import csv
from pathlib import Path


def extra_replacements(db, experiment_id, exp_dir, args):
    input_csv = exp_dir / "input" / "partitioning.csv"
    return {"INPUT_CSV": str(input_csv)}


def extra_files(db, experiment_id, exp_dir, args):
    input_dir = exp_dir / "input"
    input_dir.mkdir(parents=True, exist_ok=True)

    csv_path = input_dir / "partitioning.csv"
    if csv_path.exists():
        return

    rows = db.execute("""
        SELECT m.mouse_id,
               s_wm.sample_id AS parent_sample_id,
               NULL           AS sample_id,
               NULL           AS sample_type,
               NULL           AS weight_mg,
               NULL           AS notes
        FROM mice m
        JOIN anchors a ON a.anchor_id = m.anchor_id
        LEFT JOIN samples s_wm
               ON s_wm.anchor_id = a.anchor_id
              AND s_wm.sample_type = 'whole_muscle'
        WHERE a.project_id = (
            SELECT project_id FROM experiments WHERE experiment_id = ?
        )
        ORDER BY m.mouse_id
    """, (experiment_id,)).fetchall()

    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["mouse_id", "parent_sample_id", "sample_id", "sample_type", "weight_mg", "notes"])
        writer.writerows(rows)
