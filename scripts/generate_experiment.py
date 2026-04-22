#!/usr/bin/env python3
"""
Generate a new experiment directory and pre-populate it with:
  - YYYY-MM-DD_<name>.Rmd        printable protocol (from scripts/templates/<procedure>.Rmd)
  - input/consumables.csv        lot numbers to verify before the experiment
  - results/results.csv          blank results table ready for data entry
  - results/sample-storage.csv   blank storage locations for newly created samples
                                  (only for procedures that generate new sample IDs)

Also inserts a row into the experiments table in research.db.

Usage:
    python3 scripts/generate_experiment.py \\
        --project 2 \\
        --date 2026-04-14 \\
        --procedure rna_extraction_mito \\
        --name mito-rna-extractions \\
        --samples 8

Arguments:
    --project    project_id (see list below)
    --date       YYYY-MM-DD
    --procedure  procedure type (see list below)
    --name       kebab-case suffix for the experiment directory and Rmd filename
    --samples    number of samples (used for consumable volume calculations)
    --ids       comma-separated subject IDs to pre-fill results.csv sample_id column
                 (e.g. BB361,BB362 for mice; P001,P002 for participants) — validated against DB
    --label      optional short label included in auto-generated sample IDs
                 (e.g. 'diab', 'sg')

Projects:
    1  MATRX
    2  Small Genes with Big Potential
    3  Diabetic Small Genes
    4  MitoPilot
    5  COMIT
    6  SPRAT

"""

import argparse
import csv
import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_DIRS = {
    1: "MATRX-study",
    2: "small-genes-with-big-potential",
    3: "diabetic-small-genes",
    4: "MitoPilot",
    5: "COMIT",
    6: "SPRAT",
}

PROJECT_NAMES = {
    1: "MATRX",
    2: "Small Genes with Big Potential",
    3: "Diabetic Small Genes",
    4: "MitoPilot",
    5: "COMIT",
    6: "SPRAT",
}

TEMPLATES_DIR = Path("scripts") / "protocols" / "templates"
PROCEDURES_FILE = Path("scripts") / "procedure_meta.json"

_procedures = json.loads(PROCEDURES_FILE.read_text())


def load_procedure_meta(procedure):
    return _procedures.get(procedure)


def load_plugin(procedure):
    path = Path("scripts") / "procedures" / f"{procedure}.py"
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location(f"procedure_{procedure}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_db():
    db = sqlite3.connect("research.db")
    db.row_factory = sqlite3.Row
    return db


def get_consumables(db, project_id, procedure_type, n_samples):
    """Return list of dicts with consumable data and calculated totals."""
    rows = db.execute("""
        SELECT c.name,
               pc.amount,
               pc.unit,
               pc.scale_by,
               cl.lot_number,
               cl.expiry
        FROM procedure_consumables pc
        JOIN consumables c ON c.consumable_id = pc.consumable_id
        LEFT JOIN consumable_lots cl
            ON cl.consumable_id = pc.consumable_id
            AND cl.lot_id = (
                SELECT lot_id FROM consumable_lots
                WHERE consumable_id = pc.consumable_id
                ORDER BY date_received DESC, lot_id DESC
                LIMIT 1
            )
        WHERE pc.procedure_type = ?
          AND (pc.project_id IS NULL OR pc.project_id = ?)
        ORDER BY pc.procedure_consumable_id
    """, (procedure_type, project_id)).fetchall()

    result = []
    for row in rows:
        if row["scale_by"] == "sample":
            total = row["amount"] * n_samples
            per_label = f"{row['amount']:.4g} {row['unit']}"
            total_label = f"{total:.4g} {row['unit']}"
        else:
            total = row["amount"]
            per_label = "— (batch)"
            total_label = f"{row['amount']:.4g} {row['unit']}"

        lot = row["lot_number"] or "⚠ not recorded"
        expiry = row["expiry"] or ""

        result.append({
            "name":        row["name"],
            "per_sample":  per_label,
            "total":       total_label,
            "lot_number":  lot,
            "expiry":      expiry,
        })
    return result


def insert_experiment(db, project_id, date, procedure_type):
    cur = db.execute(
        "INSERT INTO experiments (project_id, date, procedure_type) VALUES (?, ?, ?)",
        (project_id, date, procedure_type),
    )
    db.commit()
    return cur.lastrowid


def build_sample_id(date, subject_id, tissue_suffix, label=None):
    if not tissue_suffix:
        return ""
    parts = [date, subject_id]
    if label:
        parts.append(label)
    parts.append(tissue_suffix)
    return "_".join(parts)


def consumables_to_r(consumables, n_samples):
    """Return an R code string that creates consumables_df."""
    def r_vec(items):
        quoted = [f'"{x}"' for x in items]
        return "c(" + ", ".join(quoted) + ")"

    names    = [c["name"]       for c in consumables]
    per_s    = [c["per_sample"] for c in consumables]
    totals   = [c["total"]      for c in consumables]
    lots     = [c["lot_number"] for c in consumables]
    expiries = [c["expiry"]     for c in consumables]

    return (
        f"consumables_df <- data.frame(\n"
        f"  Reagent           = {r_vec(names)},\n"
        f"  `Per Sample`      = {r_vec(per_s)},\n"
        f"  `Total ({n_samples} samples)` = {r_vec(totals)},\n"
        f"  `Lot Number`      = {r_vec(lots)},\n"
        f"  Expiry            = {r_vec(expiries)},\n"
        f"  check.names = FALSE\n"
        f")"
    )


def results_table_to_r(headers, sample_ids, n_samples):
    """Return an R code string that creates blank_results_df."""
    n = max(len(sample_ids), n_samples)
    rows = [sample_ids[i] if i < len(sample_ids) else "" for i in range(n)]

    def r_vec(items):
        quoted = [f'"{x}"' for x in items]
        return "c(" + ", ".join(quoted) + ")"

    cols = []
    for i, h in enumerate(headers):
        if i == 0 and rows:
            cols.append(f'  `{h}` = {r_vec(rows)}')
        else:
            cols.append(f'  `{h}` = rep("", {n})')

    return "results_df <- data.frame(\n" + ",\n".join(cols) + ",\n  check.names = FALSE\n)"


def render_template(template_path, replacements):
    content = Path(template_path).read_text()
    for key, value in replacements.items():
        content = content.replace(f"<<<{key}>>>", value)
    return content

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate a new experiment directory with protocol Rmd, "
                    "consumables CSV, and results CSV.",
        epilog="""
projects:
  1  MATRX
  2  Small Genes with Big Potential
  3  Diabetic Small Genes
  4  MitoPilot
  5  COMIT
  6  SPRAT
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--project",   type=int, required=True,
                        help="project_id (see list below)")
    parser.add_argument("--date",      required=True,
                        help="YYYY-MM-DD")
    parser.add_argument("--procedure", required=True,
                        help="procedure type (see list below)")
    parser.add_argument("--name",      required=True,
                        help="kebab-case suffix for the experiment directory and Rmd "
                             "filename — e.g. 'mito-rna-extraction' produces "
                             "YYYY-MM-DD_mito-rna-extraction/")
    parser.add_argument("--samples",   type=int, default=None,
                        help="number of samples (used for consumable volume calculations); "
                             "derived automatically from --ids if not provided")
    parser.add_argument("--ids",      default=None,
                        help="comma-separated subject IDs to pre-fill results.csv "
                             "(e.g. BB361,BB362 for mice; P001,P002 for participants) "
                             "— validated against DB")
    parser.add_argument("--label",     default=None,
                        help="optional short label included in auto-generated sample IDs "
                             "(e.g. 'diab', 'sg')")
    args = parser.parse_args()

    # Resolve sample count
    subject_ids = [s.strip() for s in args.ids.split(",")] if args.ids else []
    if args.samples is None:
        if not subject_ids:
            sys.exit("ERROR: --samples is required when --ids is not provided")
        args.samples = len(subject_ids)

    # Validate
    project_dir_name = PROJECT_DIRS.get(args.project)
    if not project_dir_name:
        sys.exit(f"ERROR: unknown project_id {args.project}. Valid: {list(PROJECT_DIRS)}")

    meta = load_procedure_meta(args.procedure)
    if meta is None:
        available = sorted(_procedures.keys())
        sys.exit(
            f"ERROR: unknown procedure '{args.procedure}'.\n"
            f"Valid: {', '.join(available)}"
        )

    # Validate --ids against DB before touching the filesystem
    db = get_db()
    if subject_ids:
        placeholders = ",".join("?" * len(subject_ids))
        found = (
            {r[0] for r in db.execute(
                f"SELECT mouse_id FROM mice WHERE mouse_id IN ({placeholders})",
                subject_ids).fetchall()} |
            {r[0] for r in db.execute(
                f"SELECT recruitment_id FROM participants WHERE recruitment_id IN ({placeholders})",
                subject_ids).fetchall()} |
            {r[0] for r in db.execute(
                f"SELECT culture_id FROM cell_cultures WHERE culture_id IN ({placeholders})",
                subject_ids).fetchall()}
        )
        not_found = set(subject_ids) - found
        if not_found:
            db.close()
            sys.exit(f"ERROR: IDs not found in DB: {', '.join(sorted(not_found))}")

    # Create directory
    exp_dir = (
        Path("projects") / project_dir_name / "lab-notebook" / "experiments"
        / f"{args.date}_{args.name}"
    )
    if exp_dir.exists():
        sys.exit(f"ERROR: directory already exists: {exp_dir}")

    (exp_dir / "input").mkdir(parents=True)
    (exp_dir / "results").mkdir(parents=True)
    (exp_dir / "input" / "procedure_type.txt").write_text(args.procedure + "\n")

    print(f"Created: {exp_dir}")

    experiment_id = insert_experiment(db, args.project, args.date, args.procedure)
    print(f"Inserted experiment_id={experiment_id} into experiments table")

    consumables = get_consumables(db, args.project, args.procedure, args.samples)
    if not consumables:
        print(
            f"WARNING: no consumables found for procedure '{args.procedure}', "
            f"project_id={args.project}"
        )

    # input/consumables.csv
    consumables_csv = exp_dir / "input" / "consumables.csv"
    with open(consumables_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["consumable", "lot_number", "expiry"])
        for c in consumables:
            lot = "" if c["lot_number"] == "⚠ not recorded" else c["lot_number"]
            writer.writerow([c["name"], lot, c["expiry"]])
    print(f"Consumables CSV: {consumables_csv}")

    # Build sample IDs from --ids
    tissue_suffix = meta["tissue_suffix"]
    sample_ids = []
    if subject_ids:
        if tissue_suffix:
            sample_ids = [
                build_sample_id(args.date, mid, tissue_suffix, args.label)
                for mid in subject_ids
            ]
            print(f"Sample IDs pre-filled from --ids ({len(subject_ids)} subjects)")
        else:
            # No tissue suffix — use IDs as-is to pre-fill the first results column
            sample_ids = subject_ids
            print(f"IDs pre-filled from --ids ({len(subject_ids)} subjects)")

    # Procedure-specific extra files
    plugin = load_plugin(args.procedure)
    if plugin:
        for label, path in plugin.extra_files(args, db, exp_dir, subject_ids):
            print(f"{label}: {path}")

    headers = meta["results_columns"]
    results_csv = exp_dir / "results" / "results.csv"
    n = max(len(sample_ids), args.samples)
    with open(results_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for i in range(n):
            row = [""] * len(headers)
            if sample_ids and i < len(sample_ids):
                row[0] = sample_ids[i]
            writer.writerow(row)
    print(f"Results CSV:     {results_csv}")

    # results/sample-storage.csv — only for procedures that generate new sample IDs
    if sample_ids and tissue_suffix:
        storage_csv = exp_dir / "results" / "sample-storage.csv"
        with open(storage_csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["sample_id", "freezer", "drawer", "box", "position", "date", "notes"])
            for sid in sample_ids:
                writer.writerow([sid, "", "", "", "", args.date, ""])
        print(f"Storage CSV:     {storage_csv}")

    # Rmd from template
    template_path = Path("scripts") / "protocols" / "templates" / f"{args.procedure}.Rmd"
    if template_path.exists():
        r_consumables = consumables_to_r(consumables, args.samples)
        r_results     = results_table_to_r(headers, sample_ids, args.samples)
        replacements  = {
            "PROJECT_NAME":    PROJECT_NAMES[args.project],
            "DATE":            args.date,
            "EXPERIMENT_ID":   str(experiment_id),
            "N_SAMPLES":       str(args.samples),
            "CONSUMABLES_R":   r_consumables,
            "CONSUMABLES_CSV": str(exp_dir / "input" / "consumables.csv"),
            "RESULTS_R":       r_results,
            "PROCEDURE_TYPE":  args.procedure,
        }
        if plugin:
            replacements.update(plugin.extra_replacements(args, db, subject_ids))
        rmd_content = render_template(template_path, replacements)
        rmd_path = exp_dir / f"{args.date}_{args.name}.Rmd"
        rmd_path.write_text(rmd_content)
        print(f"Protocol Rmd:    {rmd_path}")
    else:
        print(f"WARNING: no template at {template_path} — Rmd not generated")

    db.close()

    storage_note = (
        "\n  3b. Fill in results/sample-storage.csv (freezer/drawer/box/position)"
        "\n  3c. Run scripts/insert/insert_sample_storage.py to log storage locations to DB"
        if sample_ids and tissue_suffix else ""
    )
    print(f"""
Next steps:
  1. Render Rmd → print protocol
  2. Run experiment; fill in results/results.csv
  3. Verify/update input/consumables.csv with actual lot numbers used{storage_note}
  4. Run the relevant insert script for results
  5. Run scripts/insert/insert_consumable_lots.py to log lot numbers to DB
""")


if __name__ == "__main__":
    main()
