-- Institution B seed — flat legacy schema (all clinical events in one table).
-- Deliberately different from Institution A to prove the connector is general.
-- Mount as /docker-entrypoint-initdb.d/init.sql for auto-init on first startup.

-- ── Schema ────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS pt_registry (
    pt_ref       CHAR(12)    PRIMARY KEY,   -- fixed-width, right-padded with spaces
    dob          VARCHAR(10),               -- ISO date string 'YYYY-MM-DD'
    gender_code  CHAR(1)                    -- 'M', 'F', or 'U'
);

-- All clinical events live in one table, distinguished by event_class.
-- event_class values: 'DX' (diagnosis), 'RX' (medication), 'LAB' (observation),
--                     'ALLERGY', 'PROC' (procedure)
CREATE TABLE IF NOT EXISTS clinical_events (
    event_id     SERIAL      PRIMARY KEY,
    pt_ref       CHAR(12)    NOT NULL REFERENCES pt_registry(pt_ref),
    event_class  VARCHAR(10) NOT NULL,
    code         VARCHAR(50) NOT NULL,      -- ICD-10 / RxNorm / LOINC / SNOMED code
    code_system  VARCHAR(20),               -- 'ICD10', 'RXNORM', 'LOINC', 'SNOMED'
    description  TEXT,
    num_value    NUMERIC,                   -- for LAB results
    unit_val     VARCHAR(20),              -- unit for num_value
    status_flag  VARCHAR(20),
    event_date   DATE
);

-- ── Read-only role ────────────────────────────────────────────────────────────

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'umraa_reader') THEN
        -- LOGIN + password so the connector can authenticate AS the SELECT-only role
        -- (SEC-01 defense-in-depth), not as the superuser. The local-dev password is
        -- intentionally trivial; deployments override it via INSTITUTION_B_DSN.
        CREATE ROLE umraa_reader LOGIN PASSWORD 'umraa_reader';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE institution_b TO umraa_reader;
GRANT USAGE  ON SCHEMA public TO umraa_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO umraa_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO umraa_reader;

-- ── Demo patient (same clinical profile as Institution A, different layout) ───

INSERT INTO pt_registry VALUES ('DEMO-001    ', '1950-03-15', 'M');

INSERT INTO clinical_events (pt_ref, event_class, code, code_system, description, status_flag) VALUES
    ('DEMO-001    ', 'DX',     'E11',       'ICD10',  'Type 2 diabetes mellitus',               'active'),
    ('DEMO-001    ', 'DX',     'I10',       'ICD10',  'Essential (primary) hypertension',        'active'),
    ('DEMO-001    ', 'RX',     '860975',    'RXNORM', 'Metformin 500 MG Oral Tablet',            'active'),
    ('DEMO-001    ', 'RX',     '29046',     'RXNORM', 'Lisinopril 10 MG Oral Tablet',            'active'),
    ('DEMO-001    ', 'ALLERGY','372687004', 'SNOMED', 'Amoxicillin',                             'active');

INSERT INTO clinical_events (pt_ref, event_class, code, code_system, description, num_value, unit_val, status_flag) VALUES
    ('DEMO-001    ', 'LAB', '4548-4', 'LOINC', 'Hemoglobin A1c/Hemoglobin.total in Blood', 7.4, '%',    'final'),
    ('DEMO-001    ', 'LAB', '2160-0', 'LOINC', 'Creatinine [Mass/volume] in Serum',         0.9, 'mg/dL','final');

INSERT INTO clinical_events (pt_ref, event_class, code, code_system, description, status_flag, event_date) VALUES
    ('DEMO-001    ', 'PROC', '36228007', 'SNOMED', 'Ophthalmic examination and evaluation', 'completed', '2023-06-15');
