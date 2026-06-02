-- Institution A seed — EMR-style normalised schema (one table per resource type).
-- Deliberately different from Institution B to prove the connector is general.
-- Mount as /docker-entrypoint-initdb.d/init.sql for auto-init on first startup.

-- ── Schema ────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS patients (
    patient_id   VARCHAR(64)  PRIMARY KEY,
    date_of_birth DATE,
    sex          VARCHAR(10)   -- 'M', 'F', or other
);

CREATE TABLE IF NOT EXISTS diagnoses (
    diagnosis_id VARCHAR(64)  PRIMARY KEY,
    patient_id   VARCHAR(64)  NOT NULL REFERENCES patients(patient_id),
    icd10_code   VARCHAR(20)  NOT NULL,
    description  TEXT,
    status       VARCHAR(20)  DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS prescriptions (
    prescription_id VARCHAR(64) PRIMARY KEY,
    patient_id      VARCHAR(64) NOT NULL REFERENCES patients(patient_id),
    drug_name       TEXT,
    rxnorm_code     VARCHAR(20) NOT NULL,
    active          BOOLEAN     DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS lab_results (
    result_id    VARCHAR(64)  PRIMARY KEY,
    patient_id   VARCHAR(64)  NOT NULL REFERENCES patients(patient_id),
    loinc_code   VARCHAR(20)  NOT NULL,
    description  TEXT,
    value        NUMERIC,
    unit         VARCHAR(20),
    status       VARCHAR(20)  DEFAULT 'final'
);

CREATE TABLE IF NOT EXISTS drug_allergies (
    allergy_id   VARCHAR(64)  PRIMARY KEY,
    patient_id   VARCHAR(64)  NOT NULL REFERENCES patients(patient_id),
    substance    TEXT,
    snomed_code  VARCHAR(20)  NOT NULL
);

CREATE TABLE IF NOT EXISTS procedures_done (
    procedure_id VARCHAR(64)  PRIMARY KEY,
    patient_id   VARCHAR(64)  NOT NULL REFERENCES patients(patient_id),
    snomed_code  VARCHAR(20)  NOT NULL,
    description  TEXT,
    performed_on DATE
);

-- ── Read-only role ────────────────────────────────────────────────────────────

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'umraa_reader') THEN
        -- LOGIN + password so the connector can authenticate AS the SELECT-only role
        -- (SEC-01 defense-in-depth), not as the superuser. The local-dev password is
        -- intentionally trivial; deployments override it via INSTITUTION_A_DSN.
        CREATE ROLE umraa_reader LOGIN PASSWORD 'umraa_reader';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE institution_a TO umraa_reader;
GRANT USAGE  ON SCHEMA public TO umraa_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO umraa_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO umraa_reader;

-- ── Demo patient (mirrors Institution B's demo patient) ───────────────────────

INSERT INTO patients VALUES ('DEMO-001', '1950-03-15', 'M');

INSERT INTO diagnoses VALUES
    ('D001', 'DEMO-001', 'E11',    'Type 2 diabetes mellitus',               'active'),
    ('D002', 'DEMO-001', 'I10',    'Essential (primary) hypertension',        'active');

INSERT INTO prescriptions VALUES
    ('R001', 'DEMO-001', 'Metformin 500 MG Oral Tablet', '860975', TRUE),
    ('R002', 'DEMO-001', 'Lisinopril 10 MG Oral Tablet', '29046',  TRUE);

INSERT INTO lab_results VALUES
    ('L001', 'DEMO-001', '4548-4',  'Hemoglobin A1c/Hemoglobin.total in Blood', 7.4, '%',    'final'),
    ('L002', 'DEMO-001', '2160-0',  'Creatinine [Mass/volume] in Serum',         0.9, 'mg/dL','final');

INSERT INTO drug_allergies VALUES
    ('A001', 'DEMO-001', 'Amoxicillin', '372687004');

INSERT INTO procedures_done VALUES
    ('P001', 'DEMO-001', '36228007', 'Ophthalmic examination and evaluation', '2023-06-15');
