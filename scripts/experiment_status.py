#!/usr/bin/env python3
"""
Audit the relationship between experiment directories and research.db.

Reports:
  1. Experiments in the DB with no corresponding assay data rows
  2. Experiment directories whose date is not registered in the experiments table
  3. Assay rows with no experiment_id (orphaned from the registry)

Run from the research/ root:
    python3 scripts/experiment_status.py
    python3 scripts/experiment_status.py --project 2       # filter by project
    python3 scripts/experiment_status.py --verbose         # include counts for populated experiments too
"""

import argparse
import sqlite3
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PROJECT_DIRS = {
    1: "MATRX-study",
    2: "small-genes-with-big-potential",
    3: "diabetic-small-genes",
    4: "MitoPilot",
    5: "COMIT",
    6: "SPRAT",
}

# Map procedure_type → (assay table, id column)
PROCEDURE_TABLE = {
    "bca-assay":                    ("bca_assays",     "bca_assay_id"),
    "bca-assay-diluted":            ("bca_assays",     "bca_assay_id"),
    "bca_assay":                    ("bca_assays",     "bca_assay_id"),
    "cs-assay":                     ("cs_assays",        "cs_assay_id"),
    "cs_assay":                     ("cs_assays",        "cs_assay_id"),
    "cs-intactness-assay":          ("cs_intactness_assays", "cs_intactness_assay_id"),
    "dissections":                  ("dissections",    "dissection_id"),
    "mitochondrial-isolations":     ("mito_isolations","mito_isolation_id"),
    "mito_isolation":               ("mito_isolations","mito_isolation_id"),
    "rna-extractions":              ("rna_extractions","extraction_id"),
    "mitochondrial-rna-extractions":("rna_extractions","extraction_id"),
    "whole-muscle-rna-extractions": ("rna_extractions","extraction_id"),
    "rna_extraction_mito":          ("rna_extractions","extraction_id"),
    "rna_extraction_wm":            ("rna_extractions","extraction_id"),
    "rna-qc-tapestation":           ("rna_qc",         "rna_qc_id"),
    "rna-qc-nanodrop":              ("rna_qc",         "rna_qc_id"),
    "rna-qc-qubit":                 ("rna_qc",         "rna_qc_id"),
    "rna_qc_tapestation":           ("rna_qc",         "rna_qc_id"),
    "satellite_cell_isolation":     ("satellite_cell_isolations", "isolation_id"),
    "cell_differentiation":         ("cell_differentiation_runs", "diff_run_id"),
    "smiFISH_assay":                ("smiFISH_assays",  "smiFISH_id"),
}

# Directories that are not assay runs — skip silently
NON_ASSAY_KEYWORDS = {
    "partitioning", "homogenisation", "randomisation",
    "positive-control", "vo2peak", "visit-1", "visit-2",
}

def is_non_assay(dirname):
    """Return True if the directory name looks like prep/admin, not an assay run."""
    lower = dirname.lower()
    return any(kw in lower for kw in NON_ASSAY_KEYWORDS)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_db():
    db = sqlite3.connect("research.db")
    db.row_factory = sqlite3.Row
    return db


def assay_row_count(db, experiment_id, procedure_type):
    mapping = PROCEDURE_TABLE.get(procedure_type)
    if mapping is None:
        return None  # unknown procedure type — can't check
    table, _ = mapping
    row = db.execute(
        f"SELECT COUNT(*) as n FROM {table} WHERE experiment_id = ?",
        (experiment_id,)
    ).fetchone()
    return row["n"]


def get_registered_dates(db, project_id):
    """Return set of dates registered in experiments for a given project."""
    rows = db.execute(
        "SELECT date FROM experiments WHERE project_id = ?", (project_id,)
    ).fetchall()
    return {r["date"] for r in rows}


def scan_directories(project_id):
    """Return list of (date_str, dirname) for experiment directories in a project."""
    proj_dir = Path("projects") / PROJECT_DIRS[project_id] / "lab-notebook" / "experiments"
    if not proj_dir.exists():
        return []
    results = []
    for d in sorted(proj_dir.iterdir()):
        if not d.is_dir():
            continue
        name = d.name
        # Directory names start with YYYY-MM-DD
        if len(name) < 10 or name[4] != "-" or name[7] != "-":
            continue
        date_str = name[:10]
        results.append((date_str, name))
    return results

# ---------------------------------------------------------------------------
# Report sections
# ---------------------------------------------------------------------------

def report_empty_experiments(db, project_filter, verbose):
    print("=" * 70)
    print("SECTION 1 — Experiments in DB with no assay data")
    print("=" * 70)

    query = """
        SELECT e.experiment_id, p.name as project, p.project_id,
               e.date, e.procedure_type
        FROM experiments e
        JOIN projects p ON p.project_id = e.project_id
        WHERE 1=1
    """
    params = []
    if project_filter:
        query += " AND e.project_id = ?"
        params.append(project_filter)
    query += " ORDER BY e.date, p.project_id"

    rows = db.execute(query, params).fetchall()

    empty = []
    populated = []
    unknown = []

    for row in rows:
        n = assay_row_count(db, row["experiment_id"], row["procedure_type"])
        if n is None:
            unknown.append(row)
        elif n == 0:
            empty.append(row)
        else:
            populated.append((row, n))

    if empty:
        print(f"\n  {'ID':>4}  {'Date':<12}  {'Project':<30}  {'Procedure'}")
        print(f"  {'-'*4}  {'-'*12}  {'-'*30}  {'-'*30}")
        for row in empty:
            print(f"  {row['experiment_id']:>4}  {row['date']:<12}  {row['project']:<30}  {row['procedure_type']}")
    else:
        print("\n  All registered experiments have data rows. ✓")

    if unknown:
        print(f"\n  Unknown procedure type (can't check):")
        for row in unknown:
            print(f"    exp_id={row['experiment_id']}  {row['date']}  {row['procedure_type']}")

    if verbose and populated:
        print(f"\n  Populated experiments ({len(populated)}):")
        for row, n in populated:
            print(f"    {row['experiment_id']:>4}  {row['date']}  {row['project']:<30}  {row['procedure_type']}  [{n} rows]")


def report_unregistered_directories(db, project_filter, verbose):
    print("\n" + "=" * 70)
    print("SECTION 2 — Experiment directories not in the experiments table")
    print("=" * 70)

    project_ids = [project_filter] if project_filter else list(PROJECT_DIRS.keys())

    any_missing = False
    for pid in project_ids:
        if pid not in PROJECT_DIRS:
            continue
        registered = get_registered_dates(db, pid)
        dirs = scan_directories(pid)

        missing = [
            (date, name) for date, name in dirs
            if date not in registered and not is_non_assay(name)
        ]
        skipped = [
            (date, name) for date, name in dirs
            if is_non_assay(name)
        ]

        if missing:
            any_missing = True
            print(f"\n  {PROJECT_DIRS[pid]} (project_id={pid}):")
            for date, name in missing:
                print(f"    {name}")

        if verbose and skipped:
            print(f"\n  {PROJECT_DIRS[pid]} — skipped (prep/admin/visit dirs):")
            for date, name in skipped:
                print(f"    {name}")

    if not any_missing:
        print("\n  All assay directories are registered. ✓")


def report_orphaned_rows(db, project_filter):
    print("\n" + "=" * 70)
    print("SECTION 3 — Assay rows with no experiment_id (orphaned)")
    print("=" * 70)

    tables = [
        ("bca_assays",     "bca_assay_id",     "date"),
        ("cs_assays",      "cs_assay_id",       "date"),
        ("rna_extractions","extraction_id",     "date"),
        ("rna_qc",         "rna_qc_id",         "date"),
        ("mito_isolations","mito_isolation_id", "date"),
        ("dissections",    "dissection_id",     "date"),
    ]

    any_orphans = False
    for table, id_col, date_col in tables:
        try:
            rows = db.execute(
                f"SELECT COUNT(*) as n FROM {table} WHERE experiment_id IS NULL"
            ).fetchone()
            n = rows["n"]
            if n > 0:
                any_orphans = True
                print(f"\n  {table}: {n} rows with no experiment_id")
        except sqlite3.OperationalError:
            pass

    if not any_orphans:
        print("\n  No orphaned rows found. ✓")


def summary(db, project_filter):
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    query = """
        SELECT p.name, COUNT(*) as n
        FROM experiments e
        JOIN projects p ON p.project_id = e.project_id
    """
    params = []
    if project_filter:
        query += " WHERE e.project_id = ?"
        params.append(project_filter)
    query += " GROUP BY p.name ORDER BY p.name"

    rows = db.execute(query, params).fetchall()
    print()
    for row in rows:
        print(f"  {row['name']:<35} {row['n']:>3} experiments registered")

    totals = {
        "bca_assays":      db.execute("SELECT COUNT(*) as n FROM bca_assays WHERE excluded=0").fetchone()["n"],
        "cs_assays":       db.execute("SELECT COUNT(*) as n FROM cs_assays WHERE excluded=0").fetchone()["n"],
        "rna_extractions": db.execute("SELECT COUNT(*) as n FROM rna_extractions WHERE excluded=0").fetchone()["n"],
        "rna_qc":          db.execute("SELECT COUNT(*) as n FROM rna_qc WHERE excluded=0").fetchone()["n"],
        "mito_isolations": db.execute("SELECT COUNT(*) as n FROM mito_isolations").fetchone()["n"],
        "dissections":     db.execute("SELECT COUNT(*) as n FROM dissections").fetchone()["n"],
    }
    print()
    for table, n in totals.items():
        print(f"  {table:<35} {n:>4} rows (excluded=0)")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Audit experiment directories vs research.db"
    )
    parser.add_argument("--project", type=int, default=None,
                        help="Filter by project_id (1–5)")
    parser.add_argument("--verbose", action="store_true",
                        help="Also show populated experiments and skipped directories")
    args = parser.parse_args()

    db = get_db()

    report_empty_experiments(db, args.project, args.verbose)
    report_unregistered_directories(db, args.project, args.verbose)
    report_orphaned_rows(db, args.project)
    summary(db, args.project)

    db.close()
    print()


if __name__ == "__main__":
    main()
