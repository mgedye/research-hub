# Research Hub README

A personal LIMS (Laboratory Information Management System) for my research career inspired by Derek Sivers' [database management](https://github.com/sivers/sivers).

Currently in my final year of my PhD focusing on miRNA localisation to the mitochondria of skeletal muscle, but I need this to be scalable over the arc of a whole career in research.

The core idea is a single SQLite database (`research.db`) as a universal 'source of truth' across all projects, with plain-text schema and scripts as the reproducible artifact - not the data itself.
By writing everything in plain-text, all experiments can be rendered to HTML or pdf for upload to LabArchives or Syncplicity for my supervisors/PIs/institutions, but remains reproducible for any program that will inevitably come to replace them.

## Structure

- `schema.sql` — single source of truth for the database schema. Start here.
- `research.db` — SQLite database; not committed (for obvious reasons).
- `projects/` — individual projects and their respective lab notebooks.
- `scripts/` — experiment generator and insert scripts. 
  - Run `python3 scripts/generate_experiment.py --help` for procedure types and specific usage.
- `scripts/templates/` — Rmd protocol templates, one per procedure type.
- `source_protocols/` — source Word/PDF protocols from supervisors, manufacturers etc; progenitors of Rmd templates. Not committed.
- `research.Rproj` — R project for cross-project and project-specific analyses. Not committed.

## General Workflow

Every subject — a mouse, a participant, a cell culture donor — enters the database as an `anchor`.
Samples emanate from that anchor, and every downstream experiment, assay, and sequencing run links back to it.
The result is that anything can be queried across projects: which samples came from this mouse, which assays ran on this biopsy, which pipeline excluded this sample and why.

Day-to-day, the workflow is:

1. **Generate** — `generate_experiment.py` creates a dated experiment directory containing a pre-populated Rmd protocol and a blank results CSV.
2. **Print** — knit the Rmd to PDF, print, and bring it to the bench.
3. **Run** — perform the experiment, fill in the results CSV by hand or export based on equipment used.
4. **Insert** — run the relevant insert script to load results into `research.db`.
5. **Render** — return to the Rmd, update with bench notes, and re-render to PDF/HTML for upload to LabArchives or Syncplicity.

New procedure types are added by writing a template Rmd (in `scripts/templates/`) and a corresponding insert script.
New projects follow the same pattern.

## Projects

Analysis repositories that draw metadata from this hub:

### PhD

**Thesis Angle:** miRNA expression in skeletal muscle mitochondria in response to physiological (exercise) and pathological (type 1 diabetes) conditions.

*Projects hidden until publication of results.*
