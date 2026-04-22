#!/usr/bin/env python3
"""
Populate sequencing bridge tables for the first two known runs.

Inserts:
  sequencing_runs (2 rows)
    run_id=1  23C2VVLT3  — small-genes-with-big-potential  (miRNA-seq, AGRF, Dec 2025)
    run_id=2  23GJL3LT3  — diabetic-small-genes            (miRNA-seq, AGRF, Jan 2026)

  sequencing_submissions (68 rows)
    48 mito-RNA samples → run_id=1
    20 mito-RNA samples → run_id=2

  pipeline_runs (3 rows)
    pipeline_run_id=1  run_id=1  miRBase v22      (external AGRF-provided matrix)
    pipeline_run_id=2  run_id=1  MiRGeneDB 3.0   (user BLAST pipeline)
    pipeline_run_id=3  run_id=2  miRBase v22      (external AGRF-provided matrix)

  pipeline_run_exclusions (2 rows)
    BB469 and BB452 excluded from pipeline_run_id=3 (Cook's distance, diabetic QC)

Run from research/ root:
    python3 scripts/insert_sequencing_runs.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "research.db"

# ── sequencing_runs ───────────────────────────────────────────────────────────

RUNS = [
    {
        "run_id":        1,
        "run_name":      "23C2VVLT3",
        "library_type":  "miRNA-seq",
        "platform":      "NovaSeq",
        "date":          "2025-12",
        "source":        "AGRF",
        "accession":     None,
        "data_location": "local",
        "raw_data_path": "/media/matthew/hdd-passport/bioinformatics/projects/small-genes/raw-data/AGRF_NXGSQCAGRF25120155-1_23C2VVLT3",
        "notes":         "Small-genes-with-big-potential + MATRX samples on same flowcell. AGRF submission ref: AGRF_NXGSQCAGRF25120155-1",
    },
    {
        "run_id":        2,
        "run_name":      "23GJL3LT3",
        "library_type":  "miRNA-seq",
        "platform":      "NovaSeq",
        "date":          "2026-01",
        "source":        "AGRF",
        "accession":     None,
        "data_location": "local",
        "raw_data_path": "/media/matthew/hdd-passport/bioinformatics/projects/diabetic-small-genes/raw-data/AGRF_NXGSQCAGRF26010177-1_23GJL3LT3",
        "notes":         "Diabetic-small-genes samples. AGRF submission ref: AGRF_NXGSQCAGRF26010177-1",
    },
]

# ── sequencing_submissions ────────────────────────────────────────────────────
# sample_id values come from samples table (mitochondrial_rna type).

SMALL_GENES_SAMPLES = [
    "BB366_2025-12-05_mito-rna",
    "BB367_2025-12-05_mito-rna",
    "BB368_2025-12-05_mito-rna",
    "BB369_2025-12-05_mito-rna",
    "BB370_2025-12-05_mito-rna",
    "BB371_2025-12-05_mito-rna",
    "BB373_mito_rna_2025-06-16",
    "BB374_mito_rna_2025-06-16",
    "BB375_mito_rna_2025-06-17",
    "BB376_2025-12-05_mito-rna",
    "BB377_mito_rna_2025-07-28",
    "BB378_mito_rna_2025-07-28",
    "BB380_mito_rna_2025-06-16",
    "BB382_2025-12-05_mito-rna",
    "BB383_mito_rna_2025-07-28",
    "BB384_mito_rna_2025-07-28",
    "BB385_2025-12-05_mito-rna",
    "BB386_2025-12-05_mito-rna",
    "BB387_mito_rna_2025-06-16",
    "BB390_mito_rna_2025-07-28",
    "BB391_mito_rna_2025-07-28",
    "BB392_2025-12-05_mito-rna",
    "BB393_2025-12-05_mito-rna",
    "BB394_2025-12-05_mito-rna",
    "BB397_2025-12-02_mito-rna",
    "BB398_2025-12-02_mito-rna",
    "BB399_2025-12-02_mito-rna",
    "BB400_2025-12-05_mito-rna",
    "BB401_2025-12-05_mito-rna",
    "BB402_2025-12-05_mito-rna",
    "BB407_mito_rna_2025-07-28",
    "BB408_mito_rna_2025-07-28",
    "BB409_2025-12-02_mito-rna",
    "BB410_2025-12-02_mito-rna",
    "BB411_2025-12-02_mito-rna",
    "BB412_2025-12-05_mito-rna",
    "BB415_mito_rna_2025-07-28",
    "BB416_2025-12-02_mito-rna",
    "BB417_2025-12-02_mito-rna",
    "BB418_2025-12-02_mito-rna",
    "BB419_2025-12-05_mito-rna",
    "BB420_2025-12-05_mito-rna",
    "BB423_2025-12-02_mito-rna",
    "BB424_2025-12-02_mito-rna",
    "BB425_2025-12-02_mito-rna",
    "BB426_2025-12-05_mito-rna",
    "BB427_2025-12-05_mito-rna",
    "BB428_2025-12-05_mito-rna",
]

DIABETIC_SAMPLES = [
    "2026-01-21_BB443_mito-rna",
    "2026-01-21_BB444_mito-rna",
    "2026-01-21_BB445_mito-rna",
    "2026-01-21_BB446_mito-rna",
    "2026-01-21_BB447_mito-rna",
    "2026-01-21_BB448_mito-rna",
    "2026-01-21_BB449_mito-rna",
    "2026-01-21_BB450_mito-rna",
    "2026-01-21_BB451_mito-rna",
    "2026-01-21_BB452_mito-rna",
    "2026-01-21_BB461_mito-rna",
    "2026-01-21_BB462_mito-rna",
    "2026-01-21_BB463_mito-rna",
    "2026-01-21_BB465_mito-rna",
    "2026-01-21_BB466_mito-rna",
    "2026-01-21_BB467_mito-rna",
    "2026-01-21_BB468_mito-rna",
    "2026-01-21_BB469_mito-rna",
    "2026-01-21_BB470_mito-rna",
    "2026-01-21_BB471_mito-rna",
]

# ── pipeline_runs ─────────────────────────────────────────────────────────────

PIPELINE_RUNS = [
    {
        "pipeline_run_id":    1,
        "run_id":             1,
        "reference_db":       "miRBase",
        "reference_version":  "v22",
        "reference_path":     None,
        "aligner":            None,
        "counts_matrix_path": "projects/small-genes-with-big-potential/analysis/mirna_differential_expression_analysis/data-in/raw/miRNA_counts.csv",
        "notes":              "External matrix provided by AGRF. Anomalous mmu-miR-134-5p dominance (~15% of total counts) — likely miRBase v22 annotation artefact. Used for initial analysis (meeting 2026-04-16).",
    },
    {
        "pipeline_run_id":    2,
        "run_id":             1,
        "reference_db":       "MiRGeneDB",
        "reference_version":  "3.0",
        "reference_path":     None,
        "aligner":            "BLAST",
        "counts_matrix_path": "/media/matthew/hdd-passport/bioinformatics/projects/small-genes/results/count-matrix.csv",
        "notes":              "User-generated BLAST pipeline against MiRGeneDB 3.0. mmu-miR-134-5p absent (0 counts); 24 isoform entries vs 37 in miRBase v22 matrix. Arm assignments differ from miRBase matrix for some miRNAs.",
    },
    {
        "pipeline_run_id":    3,
        "run_id":             2,
        "reference_db":       "miRBase",
        "reference_version":  "v22",
        "reference_path":     None,
        "aligner":            None,
        "counts_matrix_path": "projects/diabetic-small-genes/analysis/mirna_differential_expression_analysis/data-in/raw/miRNA_counts.csv",
        "notes":              "External matrix provided by AGRF. BB469 (Cook's=592) and BB452 (Cook's=272) identified as outliers by Cook's distance; excluded at analysis level only — assay data remain valid.",
    },
]

# ── pipeline_run_exclusions ───────────────────────────────────────────────────

EXCLUSIONS = [
    {
        "pipeline_run_id": 3,
        "sample_id":       "2026-01-21_BB469_mito-rna",
        "reason":          "Cook's distance 592.67 — more than 2x the next highest sample. Substantially elevated influence on DESeq2 model fit.",
        "excluded_by":     "cooks_distance",
        "excluded_at":     "2026-04-15",
    },
    {
        "pipeline_run_id": 3,
        "sample_id":       "2026-01-21_BB452_mito-rna",
        "reason":          "Cook's distance 272.54 — substantially elevated relative to remaining samples.",
        "excluded_by":     "cooks_distance",
        "excluded_at":     "2026-04-15",
    },
]


def insert(db_path: Path) -> None:
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("PRAGMA foreign_keys = OFF")

    try:
        # Guard against re-insertion
        cur.execute("SELECT COUNT(*) FROM sequencing_runs")
        if cur.fetchone()[0] > 0:
            raise RuntimeError("sequencing_runs already has rows. Aborting to prevent duplicates.")

        # sequencing_runs
        cur.executemany(
            """INSERT INTO sequencing_runs
               (run_id, run_name, library_type, platform, date, source,
                accession, data_location, raw_data_path, notes)
               VALUES (:run_id, :run_name, :library_type, :platform, :date, :source,
                       :accession, :data_location, :raw_data_path, :notes)""",
            RUNS,
        )
        print(f"sequencing_runs: {cur.rowcount} rows inserted.")

        # sequencing_submissions — small-genes
        sg_rows = [
            {"sample_id": s, "run_id": 1, "submission_ref": "AGRF_NXGSQCAGRF25120155-1",
             "submitted_at": "2025-12", "notes": None}
            for s in SMALL_GENES_SAMPLES
        ]
        cur.executemany(
            """INSERT INTO sequencing_submissions
               (sample_id, run_id, submission_ref, submitted_at, notes)
               VALUES (:sample_id, :run_id, :submission_ref, :submitted_at, :notes)""",
            sg_rows,
        )
        print(f"sequencing_submissions (small-genes): {cur.rowcount} rows inserted.")

        # sequencing_submissions — diabetic
        diab_rows = [
            {"sample_id": s, "run_id": 2, "submission_ref": "AGRF_NXGSQCAGRF26010177-1",
             "submitted_at": "2026-01", "notes": None}
            for s in DIABETIC_SAMPLES
        ]
        cur.executemany(
            """INSERT INTO sequencing_submissions
               (sample_id, run_id, submission_ref, submitted_at, notes)
               VALUES (:sample_id, :run_id, :submission_ref, :submitted_at, :notes)""",
            diab_rows,
        )
        print(f"sequencing_submissions (diabetic): {cur.rowcount} rows inserted.")

        # pipeline_runs
        cur.executemany(
            """INSERT INTO pipeline_runs
               (pipeline_run_id, run_id, reference_db, reference_version, reference_path,
                aligner, counts_matrix_path, notes)
               VALUES (:pipeline_run_id, :run_id, :reference_db, :reference_version,
                       :reference_path, :aligner, :counts_matrix_path, :notes)""",
            PIPELINE_RUNS,
        )
        print(f"pipeline_runs: {cur.rowcount} rows inserted.")

        # pipeline_run_exclusions
        cur.executemany(
            """INSERT INTO pipeline_run_exclusions
               (pipeline_run_id, sample_id, reason, excluded_by, excluded_at)
               VALUES (:pipeline_run_id, :sample_id, :reason, :excluded_by, :excluded_at)""",
            EXCLUSIONS,
        )
        print(f"pipeline_run_exclusions: {cur.rowcount} rows inserted.")

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
