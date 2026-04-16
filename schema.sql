-- research.db schema
-- Single source of truth across all projects.
-- Enable foreign keys at connection time: PRAGMA foreign_keys = ON;

---------------------------------------------------------------------------
-- PROJECTS
---------------------------------------------------------------------------

create table projects (
    project_id   integer primary key,
    name         text not null unique check (length(name) > 0),
    description  text,
    started_at   date,
    completed_at date
);

---------------------------------------------------------------------------
-- EXPERIMENTS  (one row per lab session / experiment directory)
---------------------------------------------------------------------------

-- Maps 1:1 to lab-notebook/experiments/YYYY-MM-DD_procedure-type/ directories.
-- procedure_type matches directory suffix convention (e.g. 'mitochondrial-isolations',
-- 'bca-assay', 'rna-extractions'). Multi-procedure days with one directory share one row.
create table experiments (
    experiment_id  integer primary key,
    project_id     integer not null,  -- references projects(project_id)
    date           date    not null,
    procedure_type text,
    notes          text
);
create index experiments_project on experiments(project_id);
create index experiments_date    on experiments(date);

---------------------------------------------------------------------------
-- ANCHORS  (universal subject backbone — one row per subject)
---------------------------------------------------------------------------

create table anchors (
    anchor_id  integer primary key,
    project_id integer not null,  -- references projects(project_id)
    created_at date not null default (date('now'))
);
create index anchors_project on anchors(project_id);

---------------------------------------------------------------------------
-- ORGANISM TABLES  (one row per anchor, only the relevant table populated)
---------------------------------------------------------------------------

create table mice (
    anchor_id     integer primary key,  -- references anchors(anchor_id)
    mouse_id      text not null unique,
    sex           text check (sex in ('M', 'F', 'unknown')),
    dob           date,
    strain        text,
    genotype      text,
    intervention  text,
    group_number  integer,
    secondary_id  text,              -- institution-assigned label (e.g. ear tag, tattoo, chip number, cage)
    fate          text               -- outcome notes (e.g. date and cause of early termination)
);

create table participants (
    anchor_id      integer primary key,  -- references anchors(anchor_id)
    recruitment_id text not null unique, -- sequential enrolment ID (P001, P002, …); analogous to old anchor_id
    participant_id text unique,          -- de-identified code alias used on tubes and samples (e.g. BRKA)
    sex            text check (sex in ('M', 'F', 'unknown')),
    first_name     text,
    last_name      text,
    dob            date,
    email          text,
    phone          text,
    notes          text
);

-- MATRX screening — project-specific eligibility metadata for participants
create table matrx_screening (
    anchor_id            integer primary key,  -- references anchors(anchor_id)
    oral_contraceptives  text,
    high_blood_pressure  text,
    smoker               text,
    height_cm            real,
    weight_kg            real,
    bmi                  real,
    asthma               text,
    current_medication   text,
    medication_comments  text,
    currently_injured    text,
    injury_comments      text,
    eligible             integer check (eligible in (0, 1)),
    consented            integer check (consented in (0, 1)),
    matrx_screening_notes text
);

-- pooled or unpaired tissue specimens (MitoPilot)
create table specimens (
    anchor_id           integer primary key,  -- references anchors(anchor_id)
    specimen_id         text not null unique,
    organism            text,                 -- 'mouse', 'human', etc.
    date_acquired       date,
    proposed_experiment text,
    notes               text
);

---------------------------------------------------------------------------
-- SAMPLES  (every physical sample derived from an anchor)
---------------------------------------------------------------------------

-- sample_id is a human-readable label: 'SG-422-GASTROC', 'SG-422-MITO', 'SG-422-MITO-RNA'
create table samples (
    sample_id   text    primary key,
    anchor_id   integer not null,  -- references anchors(anchor_id)
    tissue_type text,              -- 'gastrocnemius', 'heart', 'diaphragm', 'blood', etc.
    sample_type text,              -- 'whole_muscle', 'mito_isolate', 'rna_extract', 'plasma', etc.
    date    date,
    amount  real,
    unit    text,  -- 'mg', 'g', 'ul', 'ml', etc.
    notes   text
);
create index samples_anchor on samples(anchor_id);

---------------------------------------------------------------------------
-- SAMPLE STORAGE
---------------------------------------------------------------------------

create table sample_storage (
    storage_id integer primary key,
    sample_id  text    not null,  -- references samples(sample_id)
    freezer    text,
    drawer     text,
    box        text,
    position   text,
    date    date,
    notes   text
);
create index storage_sample on sample_storage(sample_id);

---------------------------------------------------------------------------
-- ASSAYS & PROCEDURES
---------------------------------------------------------------------------

create table dissections (
    dissection_id  integer primary key,
    experiment_id  integer,          -- references experiments(experiment_id)
    anchor_id      integer not null, -- references anchors(anchor_id)
    date           date,
    bodyweight_g   real,
    notes          text
);
create index dissections_anchor on dissections(anchor_id);

create table mito_isolations (
    mito_isolation_id  integer primary key,
    experiment_id      integer,           -- references experiments(experiment_id)
    sample_id          text    not null,  -- references samples(sample_id) — tissue going in
    date               date,
    notes              text
);
create index mito_isolations_sample on mito_isolations(sample_id);

create table rna_extractions (
    extraction_id   integer primary key,
    experiment_id   integer,           -- references experiments(experiment_id)
    sample_id       text    not null,  -- references samples(sample_id)
    date            date,
    method           text,             -- 'trizol', 'zymo', etc.
    trizol_vol_ul    real,             -- trizol extractions only
    etoh_vol_ul      real,             -- trizol extractions only
    elution_vol_ul   real,
    dilution_factor  real,
    dnase_treatment  integer default 0, -- 1 if on-column or post-extraction DNase applied
    excluded         integer default 0,
    exclusion_reason text,
    notes            text
);
create index rna_extractions_sample on rna_extractions(sample_id);

-- instrument: 'tapestation', 'nanodrop', 'qubit'
-- tapestation: rin, ratio_28s_18s, concentration (pg/ul mito / ng/ul wm), well
-- nanodrop: concentration (ng/ul), a260_280, a260_230
create table rna_qc (
    rna_qc_id          integer primary key,
    experiment_id      integer,           -- references experiments(experiment_id)
    sample_id          text    not null,  -- references samples(sample_id) — the RNA extract
    date               date,
    instrument         text    not null,
    well               text,              -- plate/chip position (tapestation)
    rin                real,
    ratio_28s_18s      real,
    concentration      real,
    concentration_unit text,              -- 'pg/ul' (tapestation mito), 'ng/ul' (tapestation wm, nanodrop)
    a260_280           real,
    a260_230           real,
    excluded           integer default 0,
    exclusion_reason   text,
    notes              text
);
create index rna_qc_sample on rna_qc(sample_id);

create table bca_assays (
    bca_assay_id          integer primary key,
    experiment_id         integer,           -- references experiments(experiment_id)
    sample_id             text    not null,  -- references samples(sample_id)
    date                  date,
    dilution_factor       real,
    protein_concentration real,
    unit                  text,             -- 'mg/ml'
    excluded              integer default 0,
    exclusion_reason      text,
    notes                 text
);
create index bca_assays_sample on bca_assays(sample_id);

create table cs_assays (
    cs_assay_id           integer primary key,
    experiment_id         integer,           -- references experiments(experiment_id)
    sample_id             text    not null,  -- references samples(sample_id)
    date                  date,
    cs_umol_min_g_protein real,
    excluded              integer default 0,
    exclusion_reason      text,
    notes                 text
);
create index cs_assays_sample on cs_assays(sample_id);

create table cs_intactness_assays (
    cs_intactness_assay_id         integer primary key,
    experiment_id                  integer,           -- references experiments(experiment_id)
    sample_id                      text    not null,  -- references samples(sample_id)
    date                           date,
    cs_umol_min_g_protein_unlysed  real,              -- no Triton-X
    cs_umol_min_g_protein_lysed    real,              -- with Triton-X; intactness_ratio = unlysed / lysed
    excluded                       integer default 0,
    exclusion_reason               text,
    notes                          text
);
create index cs_intactness_assays_sample on cs_intactness_assays(sample_id);

-- visit 1: VO2peak test session metadata
create table matrx_visit_1 (
    vo2peak_input_id      integer primary key,
    anchor_id             integer not null,  -- references anchors(anchor_id)
    date                  date,
    start_time            text,
    matrx_visit_1_notes   text
);
create index matrx_visit_1_anchor on matrx_visit_1(anchor_id);

-- visit 1: 30-second time-series data during VO2peak test
create table vo2peak_data (
    vo2peak_data_id  integer primary key,
    vo2peak_input_id integer not null,  -- references vo2peak_inputs(vo2peak_input_id)
    interval         text,
    time_seconds     real,
    workload_w       real,
    vo2_ml_min       real,
    vo2_ml_min_kg    real,
    hr_bpm           real,
    rer              real
);
create index vo2peak_data_input on vo2peak_data(vo2peak_input_id);

-- visit 1: summary outcomes derived from VO2peak test
create table vo2peak_summaries (
    vo2peak_summary_id               integer primary key,
    vo2peak_input_id                 integer not null unique,  -- references vo2peak_inputs(vo2peak_input_id)
    vo2_peak_ml_min                  real,
    vo2_peak_ml_min_kg               real,
    peak_hr_bpm                      integer,
    peak_workload_w                  integer,
    vo2peak_70_percent_ml_min        real,
    hr_at_70_percent_vo2peak         integer,
    workload_at_70_percent_vo2peak_w integer,
    vo2peak_summaries_notes          text
);

-- visit 2: session-level bridge — one row per participant
-- absorbs submaximal_inputs (starting_power_w derived from vo2peak_summaries.workload_at_70_percent_vo2peak_w)
create table matrx_visit_2 (
    tissue_collection_id  integer primary key,
    anchor_id             integer not null,  -- references anchors(anchor_id)
    date                  date,
    arrival_time          text,
    bike_start_time       text,
    bike_finish_time      text,
    matrx_visit_2_notes   text               -- e.g. did not attend, food offered, follow-up status, biopsy completeness
);
create index matrx_visit_2_anchor on matrx_visit_2(anchor_id);

-- visit 2: VO2 readings at discrete timepoints during submaximal cycling bout
create table matrx_submaximal_vo2 (
    matrx_submaximal_vo2_id  integer primary key,
    tissue_collection_id     integer not null,  -- references matrx_visit_2(tissue_collection_id)
    time_interval            text,              -- 'start', '25_percent', '50_percent', '75_percent'
    vo2_ml_min               real,
    power_output_w               real,
    matrx_submaximal_vo2_notes   text
);
create index matrx_submaximal_vo2_tc on matrx_submaximal_vo2(tissue_collection_id);


-- visit 2: one row per muscle biopsy (pre / post / recovery)
create table matrx_biopsies (
    biopsy_id            integer primary key,
    tissue_collection_id integer not null,  -- references matrx_visit_2
    timepoint            text check (timepoint in ('pre', 'post', 'recovery')),
    time                 text,
    total_weight_mg      real,
    needle_number        integer,
    leg                  text,
    matrx_biopsies_notes text
);
create index matrx_biopsies_tc on matrx_biopsies(tissue_collection_id);

-- visit 2: one row per aliquot from a biopsy (mito / fish / wm / oth)
create table matrx_biopsy_aliquots (
    aliquot_id   integer primary key,
    biopsy_id    integer not null,  -- references matrx_biopsies
    aliquot_type text check (aliquot_type in ('mito', 'fish', 'wm', 'oth')),
    weight_mg    real,
    sample_id    text               -- references samples(sample_id)
);
create index matrx_biopsy_aliquots_biopsy on matrx_biopsy_aliquots(biopsy_id);

---------------------------------------------------------------------------
-- CONSUMABLES
---------------------------------------------------------------------------

-- master list of all reagents and materials
create table consumables (
    consumable_id  integer primary key,
    name           text not null unique,
    supplier       text,
    catalogue_no   text,
    notes          text
);

-- each lot received for a consumable
create table consumable_lots (
    lot_id         integer primary key,
    consumable_id  integer not null,  -- references consumables(consumable_id)
    lot_number     text not null,
    expiry         date,
    date_received  date,
    notes          text
);
create index consumable_lots_consumable on consumable_lots(consumable_id);

-- protocol recipe: amounts per sample (or per batch) for each procedure type
create table procedure_consumables (
    procedure_consumable_id  integer primary key,
    procedure_type           text not null,  -- 'mito_isolation', 'rna_extraction_mito', 'bca_assay', etc.
    consumable_id            integer not null,  -- references consumables(consumable_id)
    project_id               integer,          -- NULL = applies to all projects; set if project-specific
    amount                   real,
    unit                     text,             -- 'ul', 'ml', 'piece', etc.
    scale_by                 text,             -- 'sample' = multiply by n_samples; 'batch' = fixed per run
    notes                    text
);
create index procedure_consumables_type on procedure_consumables(procedure_type);
create index procedure_consumables_consumable on procedure_consumables(consumable_id);

-- links specific lots to specific assay/procedure runs
create table assay_consumables (
    assay_consumable_id  integer primary key,
    lot_id               integer not null,  -- references consumable_lots(lot_id)
    procedure_type       text not null,     -- 'mito_isolation', 'bca_assay', etc.
    procedure_id         integer not null,  -- ID from the relevant procedure table
    notes                text
);
create index assay_consumables_lot on assay_consumables(lot_id);
create index assay_consumables_procedure on assay_consumables(procedure_type, procedure_id);

---------------------------------------------------------------------------
-- SEQUENCING
---------------------------------------------------------------------------

-- one row per sequencing run (batch from facility or public dataset download)
-- data_location values: 'local', 'ssh', 'sra', 'cloud'
-- source values:        'AGRF', 'GEO', 'SRA', 'ENA', 'in-house'
-- library_type values:  'miRNA-seq', 'mRNA-seq', 'lncRNA-seq', 'RNA-seq',
--                       'WGS', 'WES', 'mtDNA-seq', 'ATAC-seq'
-- raw_data_path:        local absolute path, user@host:/path (ssh),
--                       SRA run accession (sra), or s3://bucket/path (cloud)
create table sequencing_runs (
    run_id         integer primary key,
    run_name       text    not null,  -- flowcell ID (e.g. 23C2VVLT3) or study accession
    library_type   text,
    platform       text,              -- 'NovaSeq', 'NextSeq', 'HiSeq', etc.
    date           date,
    source         text,              -- 'AGRF', 'GEO', 'SRA', 'ENA', 'in-house'
    accession      text,              -- public accession if applicable (GSE*, SRP*, PRJNA*)
    data_location  text,              -- 'local', 'ssh', 'sra', 'cloud'
    raw_data_path  text,              -- path or URI to raw data
    notes          text
);

-- links each submitted sample to its sequencing run
-- one row per sample per run; notes captures submission reference (e.g. AGRF job number)
create table sequencing_submissions (
    submission_id   integer primary key,
    sample_id       text    not null,  -- references samples(sample_id)
    run_id          integer not null,  -- references sequencing_runs(run_id)
    submission_ref  text,              -- facility job/submission ID (e.g. AGRF_NXGSQCAGRF25120155-1)
    submitted_at    date,
    notes           text
);
create index sequencing_submissions_sample on sequencing_submissions(sample_id);
create index sequencing_submissions_run    on sequencing_submissions(run_id);

-- one row per bioinformatics pipeline run against a specific reference database
-- multiple rows per run_id when comparing databases (e.g. miRBase vs MiRGeneDB)
-- reference_path: path to FASTA/index used for alignment
create table pipeline_runs (
    pipeline_run_id    integer primary key,
    run_id             integer not null,  -- references sequencing_runs(run_id)
    reference_db       text    not null,  -- 'miRBase', 'MiRGeneDB', 'GENCODE', 'Ensembl'
    reference_version  text,              -- 'v22', '3.0', 'v44', etc.
    reference_path     text,              -- path to reference FASTA/index on HDD or remote
    aligner            text,              -- 'BLAST', 'STAR', 'kallisto', 'bowtie', 'mirDeep2'
    counts_matrix_path text,              -- path to derived counts matrix
    notes              text
);
create index pipeline_runs_run on pipeline_runs(run_id);

-- per-sample exclusions scoped to a specific pipeline run
-- does NOT affect assay tables (cs_assays, rna_extractions etc.) — those data remain valid
-- excluded_by values: 'cooks_distance', 'pca_outlier', 'rna_qc', 'manual'
create table pipeline_run_exclusions (
    exclusion_id     integer primary key,
    pipeline_run_id  integer not null,  -- references pipeline_runs(pipeline_run_id)
    sample_id        text    not null,  -- references samples(sample_id)
    reason           text,
    excluded_by      text,
    excluded_at      date
);
create index pipeline_run_exclusions_run    on pipeline_run_exclusions(pipeline_run_id);
create index pipeline_run_exclusions_sample on pipeline_run_exclusions(sample_id);

-- samples from external/public datasets where no physical sample exists in the lab
-- use when source is GEO, SRA, collaborator data, or re-analysed published studies
-- external_sample_id: GSM*/SRR* accession or study-assigned label
-- condition: experimental group label as defined in the source study
-- metadata columns (age, bmi etc.) can be added with ALTER TABLE ADD COLUMN when needed
create table external_samples (
    external_sample_id  text    primary key,
    run_id              integer not null,  -- references sequencing_runs(run_id)
    study_accession     text,              -- parent study accession (GSE*, SRP*, PRJNA*)
    organism            text,              -- 'Homo sapiens', 'Mus musculus'
    tissue              text,              -- 'skeletal muscle', 'mitochondria', etc.
    condition           text,              -- experimental group label
    sex                 text,
    notes               text
);
create index external_samples_run on external_samples(run_id);

---------------------------------------------------------------------------
-- SPRAT — cell culture and smiFISH probe validation
---------------------------------------------------------------------------

-- Master record for each frozen cell stock (one row per passage per donor).
-- culture_id is human-readable: e.g. 'SKM-001-P0', 'SKM-001-P1'.
-- participant_id links to participants(participant_id) when the donor is already
-- in the DB (e.g. MATRX biopsy donor); donor_label is a fallback for new donors.
create table cell_cultures (
    culture_id         text    primary key,           -- e.g. 'SKM-001-P0', 'SKM-001-P1'
    donor_label        text,                          -- donor identifier (fresh or archived; not in participants table)
    passage            integer not null,              -- 0 = P0, 1 = P1, etc.
    parent_culture_id  text,                          -- references cell_cultures(culture_id); null for P0
    date_frozen        date,
    n_vials            integer,
    storage_box        text,
    notes              text
);

-- Satellite cell isolation procedure: biopsy → digestion → pre-plating → P0 stock.
-- One row per isolation; culture_id references the P0 cell_cultures record produced.
create table satellite_cell_isolations (
    isolation_id           integer primary key,
    experiment_id          integer,                   -- references experiments(experiment_id)
    culture_id             text    not null,          -- references cell_cultures(culture_id)
    biopsy_mass_mg         real,
    preplating_duration_hr real,                      -- protocol default: 3 hr
    excluded               integer default 0 check (excluded in (0, 1)),
    exclusion_reason       text,
    notes                  text
);
create index satellite_cell_isolations_culture on satellite_cell_isolations(culture_id);

-- Differentiation run: thaw a vial → growth media → DM1 → DM2 (D0) → harvest (D5).
-- Spans multiple days; all phase-transition dates recorded here.
-- plate_format: '6-well', '8-well-chamber-slide', '10cm', etc.
create table cell_differentiation_runs (
    diff_run_id            integer primary key,
    experiment_id          integer,                   -- references experiments(experiment_id); the seeding day
    culture_id             text    not null,          -- references cell_cultures(culture_id); vial thawed
    plate_format           text,
    n_wells                integer,
    seeding_date           date,                      -- day seeded into growth media on matrigel
    dm1_start_date         date,                      -- switched to DM1 (target 80–85% confluent)
    dm2_start_date         date,                      -- D0: switched to DM2
    harvest_date           date,                      -- actual harvest date (D5 target)
    confluency_at_dm1_pct  real,                      -- observed confluency at DM1 switch
    confluency_at_dm2_pct  real,                      -- observed confluency at DM2 switch (target: lined up)
    excluded               integer default 0 check (excluded in (0, 1)),
    exclusion_reason       text,
    notes                  text
);
create index cell_differentiation_runs_culture on cell_differentiation_runs(culture_id);

-- smiFISH assay results: one row per well per probe.
-- diff_run_id links back to the differentiation run the cells came from.
-- spots_per_cell_* are the primary probe validation metrics.
-- signal_intensity_mean and snr_mean are optional outputs from image analysis software.
create table smiFISH_assays (
    smiFISH_id             integer primary key,
    experiment_id          integer,                   -- references experiments(experiment_id)
    diff_run_id            integer not null,          -- references cell_differentiation_runs(diff_run_id)
    well_id                text,                      -- well/chamber position (e.g. 'A1', 'well_3')
    probe_name             text,                      -- probe set identifier
    target_gene            text,                      -- target mRNA / gene symbol
    fluorescent_channel    text,                      -- 'cy3', 'cy5', 'alexa488', etc.
    n_cells_analyzed       integer,
    spots_per_cell_mean    real,
    spots_per_cell_sd      real,
    signal_intensity_mean  real,                      -- optional: from image analysis software
    snr_mean               real,                      -- signal-to-noise ratio, optional
    image_path             text,                      -- path to raw images or analysis output directory
    excluded               integer default 0 check (excluded in (0, 1)),
    exclusion_reason       text,
    notes                  text
);
create index smiFISH_assays_diff_run on smiFISH_assays(diff_run_id);
