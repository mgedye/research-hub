import csv


def extra_files(args, db, exp_dir, subject_ids):
    if not subject_ids:
        return []
    path = exp_dir / "input" / "muscle_partitioning.csv"
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["mouse_id", "weight_mg"])
        for mid in subject_ids:
            writer.writerow([mid, ""])
    return [("Muscle partitioning CSV", path)]


def extra_replacements(args, db, subject_ids):
    return {}
