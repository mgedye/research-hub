#!/usr/bin/env python3
"""
Insert MATRX sequencing data into research.db.

Steps:
  1. Insert 3 mitochondrial_rna samples for AKTS (anchor_id=141, exp_id=74)
     — extracted 2025-12-17, same pattern as all other MATRX mito RNA samples
  2. Insert 39 sequencing_submissions rows (13 participants × 3 timepoints)
     — run_id=1 (23C2VVLT3), submission_ref=AGRF_NXGSQCAGRF25120155-2
  3. Insert pipeline_runs row (pipeline_run_id=4)
     — MATRX human miRNA-seq, miRBase v22, user BLAST pipeline

Note: BKRA in AGRF filenames = BRKA in DB (typo in AGRF delivery)
      GKNR in AGRF filenames = GNKR in DB (typo in AGRF delivery)
      BHXA, DFCD, HDZW — have mito RNA but were NOT sent for sequencing

Run from research/ root:
    python3 scripts/insert_matrx_sequencing.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "research.db"

# ── 1. AKTS mitochondrial_rna samples ────────────────────────────────────────

AKTS_SAMPLES = [
    {"sample_id": "2025-12-17_AKTS_Pre_MitoRNA",      "anchor_id": 141, "sample_type": "mitochondrial_rna", "date": "2025-12-17"},
    {"sample_id": "2025-12-17_AKTS_Post_MitoRNA",     "anchor_id": 141, "sample_type": "mitochondrial_rna", "date": "2025-12-17"},
    {"sample_id": "2025-12-17_AKTS_Recovery_MitoRNA", "anchor_id": 141, "sample_type": "mitochondrial_rna", "date": "2025-12-17"},
]

# ── 2. sequencing_submissions — all 39 MATRX samples ─────────────────────────
# run_id=1 is shared flowcell 23C2VVLT3 (small-genes + MATRX on same run)
# sample_ids from DB; run_id=1 (flowcell 23C2VVLT3)

MATRX_SUBMISSIONS = [
    # AKTS (Dec 17)
    "2025-12-17_AKTS_Pre_MitoRNA",
    "2025-12-17_AKTS_Post_MitoRNA",
    "2025-12-17_AKTS_Recovery_MitoRNA",
    # AVNI (Dec 09)
    "2025-12-09_AVNI_Pre_MitoRNA",
    "2025-12-09_AVNI_Post_MitoRNA",
    "2025-12-09_AVNI_Recovery_MitoRNA",
    # BRKA (Dec 08) — BKRA in AGRF filenames
    "2025-12-08_BRKA_Pre_MitoRNA",
    "2025-12-08_BRKA_Post_MitoRNA",
    "2025-12-08_BRKA_Recovery_MitoRNA",
    # CTLQ (Dec 15)
    "2025-12-15_CTLQ_Pre_MitoRNA",
    "2025-12-15_CTLQ_Post_MitoRNA",
    "2025-12-15_CTLQ_Recovery_MitoRNA",
    # EOPA (Dec 15)
    "2025-12-15_EOPA_Pre_MitoRNA",
    "2025-12-15_EOPA_Post_MitoRNA",
    "2025-12-15_EOPA_Recovery_MitoRNA",
    # GNKR (Dec 15) — GKNR in AGRF filenames
    "2025-12-15_GNKR_Pre_MitoRNA",
    "2025-12-15_GNKR_Post_MitoRNA",
    "2025-12-15_GNKR_Recovery_MitoRNA",
    # KYUP (Dec 08)
    "2025-12-08_KYUP_Pre_MitoRNA",
    "2025-12-08_KYUP_Post_MitoRNA",
    "2025-12-08_KYUP_Recovery_MitoRNA",
    # PLFF (Dec 09)
    "2025-12-09_PLFF_Pre_MitoRNA",
    "2025-12-09_PLFF_Post_MitoRNA",
    "2025-12-09_PLFF_Recovery_MitoRNA",
    # QOAC (Dec 09)
    "2025-12-09_QOAC_Pre_MitoRNA",
    "2025-12-09_QOAC_Post_MitoRNA",
    "2025-12-09_QOAC_Recovery_MitoRNA",
    # RAOC (Dec 15)
    "2025-12-15_RAOC_Pre_MitoRNA",
    "2025-12-15_RAOC_Post_MitoRNA",
    "2025-12-15_RAOC_Recovery_MitoRNA",
    # STUW (Dec 09)
    "2025-12-09_STUW_Pre_MitoRNA",
    "2025-12-09_STUW_Post_MitoRNA",
    "2025-12-09_STUW_Recovery_MitoRNA",
    # VBEW (Dec 08)
    "2025-12-08_VBEW_Pre_MitoRNA",
    "2025-12-08_VBEW_Post_MitoRNA",
    "2025-12-08_VBEW_Recovery_MitoRNA",
    # WGAC (Dec 08)
    "2025-12-08_WGAC_Pre_MitoRNA",
    "2025-12-08_WGAC_Post_MitoRNA",
    "2025-12-08_WGAC_Recovery_MitoRNA",
]


MATRX_PIPELINE_RUN = {
    "pipeline_run_id":    4,
    "run_id":             1,
    "reference_db":       "miRBase",
    "reference_version":  "v22",
    "reference_path":     "/media/matthew/hdd-passport/bioinformatics/databases/miRbase/mirbase_hsa_mature",
    "aligner":            "BLAST",
    "counts_matrix_path": "/media/matthew/hdd-passport/bioinformatics/projects/matrx/results/count-matrix.csv",
    "notes":              "MATRX human miRNA-seq. Re-run by user 2026-04-15 for consistency (original counts matrix was externally provided by AGRF). 48,885 mature sequences in reference (miRBase v22).",
}


def insert(db_path: Path) -> None:
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("PRAGMA foreign_keys = OFF")

    try:
        # ── AKTS samples ──────────────────────────────────────────────────────
        existing = {
            r[0] for r in cur.execute("SELECT sample_id FROM samples WHERE anchor_id = 141 AND sample_type = 'mitochondrial_rna'")
        }
        to_insert = [s for s in AKTS_SAMPLES if s["sample_id"] not in existing]

        if to_insert:
            cur.executemany(
                """INSERT INTO samples (sample_id, anchor_id, sample_type, date)
                   VALUES (:sample_id, :anchor_id, :sample_type, :date)""",
                to_insert,
            )
            print(f"samples (AKTS mito RNA): {cur.rowcount} rows inserted.")
        else:
            print("samples (AKTS mito RNA): already present, skipping.")

        # ── sequencing_submissions ────────────────────────────────────────────
        existing_subs = {
            r[0] for r in cur.execute(
                "SELECT sample_id FROM sequencing_submissions WHERE run_id = 1"
                "  AND submission_ref = 'AGRF_NXGSQCAGRF25120155-2'"
            )
        }
        sub_rows = [
            {
                "sample_id":      s,
                "run_id":         1,
                "submission_ref": "AGRF_NXGSQCAGRF25120155-2",
                "submitted_at":   "2025-12",
                "notes":          None,
            }
            for s in MATRX_SUBMISSIONS
            if s not in existing_subs
        ]

        if sub_rows:
            cur.executemany(
                """INSERT INTO sequencing_submissions
                   (sample_id, run_id, submission_ref, submitted_at, notes)
                   VALUES (:sample_id, :run_id, :submission_ref, :submitted_at, :notes)""",
                sub_rows,
            )
            print(f"sequencing_submissions (MATRX): {cur.rowcount} rows inserted.")
        else:
            print("sequencing_submissions (MATRX): already present, skipping.")

        # ── pipeline_runs (MATRX) ─────────────────────────────────────────────
        existing_pr = cur.execute(
            "SELECT COUNT(*) FROM pipeline_runs WHERE pipeline_run_id = 4"
        ).fetchone()[0]

        if existing_pr == 0:
            cur.execute(
                """INSERT INTO pipeline_runs
                   (pipeline_run_id, run_id, reference_db, reference_version,
                    reference_path, aligner, counts_matrix_path, notes)
                   VALUES (:pipeline_run_id, :run_id, :reference_db, :reference_version,
                           :reference_path, :aligner, :counts_matrix_path, :notes)""",
                MATRX_PIPELINE_RUN,
            )
            print("pipeline_runs (MATRX, pipeline_run_id=4): 1 row inserted.")
        else:
            print("pipeline_runs (MATRX, pipeline_run_id=4): already present, skipping.")

        con.commit()
        print("\nInsert complete.")

    except Exception:
        con.rollback()
        raise
    finally:
        cur.execute("PRAGMA foreign_keys = ON")
        con.close()


if __name__ == "__main__":
    insert(DB_PATH)
