-- =====================================================================
-- SYNCRA Payroll Engine - Core Technical Infrastructure
-- Architecture: Deterministic, Bitemporal, Immutable Snapshot Engine
-- Compliance: Separation of Technical Engine & Legal Core
-- Version: 1.0.0 (October 2026)
-- =====================================================================

-- 00. Enable cryptographic extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 01. Enums for Cycle States and Rule Legal Status
DO $$ BEGIN
    CREATE TYPE cycle_state AS ENUM ('SAISIE', 'EN_CALCUL', 'CLOTURE');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE rule_status AS ENUM (
      'EN_ATTENTE_N1',
      'BLOQUE',
      'A_DOCUMENTER',
      'A_ARBITRER',
      'CIBLE_CONDITIONNELLE',
      'VALIDE_HORS_PRODUCTION'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 02. Dossiers (Independent Isolated Multi-Tenant Client Dossier)
CREATE TABLE IF NOT EXISTS dossier (
  dossier_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code TEXT NOT NULL UNIQUE,
  label TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 03. Payroll Cycles with State Management
CREATE TABLE IF NOT EXISTS payroll_cycle (
  cycle_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dossier_id UUID NOT NULL REFERENCES dossier(dossier_id) ON DELETE CASCADE,
  employee_id UUID NOT NULL,
  period_start DATE NOT NULL,
  period_end DATE NOT NULL,
  state cycle_state NOT NULL DEFAULT 'SAISIE',
  current_manifest_hash TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  closed_at TIMESTAMPTZ,
  CONSTRAINT payroll_cycle_period_ck CHECK (period_end >= period_start)
);

CREATE INDEX IF NOT EXISTS payroll_cycle_dossier_idx ON payroll_cycle(dossier_id);
CREATE INDEX IF NOT EXISTS payroll_cycle_employee_idx ON payroll_cycle(employee_id);

-- 04. Bitemporal Values (Valid Time vs. Transaction Time)
CREATE TABLE IF NOT EXISTS bitemporal_value (
  value_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dossier_id UUID NOT NULL REFERENCES dossier(dossier_id) ON DELETE CASCADE,
  scope_type TEXT NOT NULL,
  scope_id UUID NOT NULL,
  field_code TEXT NOT NULL,
  value_json JSONB NOT NULL,
  valid_from DATE NOT NULL,
  valid_to DATE,
  tx_from TIMESTAMPTZ NOT NULL DEFAULT now(),
  tx_to TIMESTAMPTZ,
  source_ref TEXT,
  created_by TEXT,
  CONSTRAINT bitemporal_valid_range_ck CHECK (valid_to IS NULL OR valid_to >= valid_from),
  CONSTRAINT bitemporal_tx_range_ck CHECK (tx_to IS NULL OR tx_to >= tx_from)
);

CREATE INDEX IF NOT EXISTS bitemporal_scope_idx ON bitemporal_value(dossier_id, scope_type, scope_id, field_code);
CREATE INDEX IF NOT EXISTS bitemporal_valid_idx ON bitemporal_value(valid_from, valid_to);
CREATE INDEX IF NOT EXISTS bitemporal_tx_idx ON bitemporal_value(tx_from, tx_to);

-- 05. Rule Registry (Gate 1 Enforcer)
CREATE TABLE IF NOT EXISTS rule_registry (
  rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code TEXT NOT NULL UNIQUE,
  label TEXT NOT NULL,
  status rule_status NOT NULL,
  implementation_autorisee BOOLEAN NOT NULL DEFAULT false,
  ast_version TEXT,
  legal_source_ref TEXT,
  legal_article_ref TEXT,
  valid_from DATE,
  valid_to DATE,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT rule_no_prod_without_flag_ck CHECK (
    (implementation_autorisee = false)
    OR (status IN ('VALIDE_HORS_PRODUCTION'))
  )
);

-- 06. Rule Dependencies (DAG)
CREATE TABLE IF NOT EXISTS rule_dependency (
  rule_id UUID NOT NULL REFERENCES rule_registry(rule_id) ON DELETE CASCADE,
  depends_on_rule_id UUID NOT NULL REFERENCES rule_registry(rule_id) ON DELETE RESTRICT,
  PRIMARY KEY (rule_id, depends_on_rule_id),
  CONSTRAINT rule_dependency_no_self_ck CHECK (rule_id <> depends_on_rule_id)
);

-- 07. Manifests (Frozen Inputs) and Snapshots (Frozen Results)
CREATE TABLE IF NOT EXISTS manifest (
  manifest_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cycle_id UUID NOT NULL REFERENCES payroll_cycle(cycle_id) ON DELETE CASCADE,
  dossier_id UUID NOT NULL REFERENCES dossier(dossier_id) ON DELETE CASCADE,
  manifest_json JSONB NOT NULL,
  manifest_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS manifest_hash_uq ON manifest(manifest_hash);
CREATE INDEX IF NOT EXISTS manifest_cycle_idx ON manifest(cycle_id);

CREATE TABLE IF NOT EXISTS snapshot (
  snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cycle_id UUID NOT NULL REFERENCES payroll_cycle(cycle_id) ON DELETE CASCADE,
  dossier_id UUID NOT NULL REFERENCES dossier(dossier_id) ON DELETE CASCADE,
  manifest_id UUID NOT NULL REFERENCES manifest(manifest_id) ON DELETE RESTRICT,
  snapshot_json JSONB NOT NULL,
  snapshot_hash TEXT NOT NULL,
  state cycle_state NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  closed_at TIMESTAMPTZ,
  CONSTRAINT snapshot_state_ck CHECK (state IN ('EN_CALCUL', 'CLOTURE'))
);

CREATE UNIQUE INDEX IF NOT EXISTS snapshot_hash_uq ON snapshot(snapshot_hash);
CREATE INDEX IF NOT EXISTS snapshot_cycle_idx ON snapshot(cycle_id);

-- 08. Calculation Attempts (Audit and Diagnostics)
CREATE TABLE IF NOT EXISTS calc_attempt (
  attempt_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cycle_id UUID NOT NULL REFERENCES payroll_cycle(cycle_id) ON DELETE CASCADE,
  dossier_id UUID NOT NULL REFERENCES dossier(dossier_id) ON DELETE CASCADE,
  manifest_id UUID NOT NULL REFERENCES manifest(manifest_id) ON DELETE RESTRICT,
  snapshot_id UUID REFERENCES snapshot(snapshot_id) ON DELETE SET NULL,
  engine_version TEXT NOT NULL,
  status TEXT NOT NULL, -- e.g., 'SUCCESS', 'FAILED_GATE_1', 'FAILED_DIAGNOSTIC'
  diagnostics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS calc_attempt_cycle_idx ON calc_attempt(cycle_id);
CREATE INDEX IF NOT EXISTS calc_attempt_dossier_idx ON calc_attempt(dossier_id);

-- 09. Rule Execution Trace
CREATE TABLE IF NOT EXISTS rule_execution_trace (
  trace_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  attempt_id UUID NOT NULL REFERENCES calc_attempt(attempt_id) ON DELETE CASCADE,
  rule_id UUID NOT NULL REFERENCES rule_registry(rule_id),
  input_json JSONB,
  output_json JSONB,
  anomaly_code TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS rule_execution_attempt_idx ON rule_execution_trace(attempt_id);
CREATE INDEX IF NOT EXISTS rule_execution_rule_idx ON rule_execution_trace(rule_id);

-- 10. Data Label Catalog (Trilingual Dictionary ar, fr, en)
CREATE TABLE IF NOT EXISTS data_label_catalog (
  label_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dossier_id UUID REFERENCES dossier(dossier_id) ON DELETE CASCADE,
  label_code TEXT NOT NULL,
  lang TEXT NOT NULL,
  label_value TEXT NOT NULL,
  valid_from DATE,
  valid_to DATE,
  tx_from TIMESTAMPTZ NOT NULL DEFAULT now(),
  tx_to TIMESTAMPTZ,
  CONSTRAINT data_label_lang_ck CHECK (lang IN ('ar', 'fr', 'en'))
);

CREATE UNIQUE INDEX IF NOT EXISTS data_label_catalog_uq
  ON data_label_catalog(COALESCE(dossier_id, '00000000-0000-0000-0000-000000000000'::uuid), label_code, lang, tx_from);

-- 11. Render Artifacts (Idempotency and Binary Output Registry)
CREATE TABLE IF NOT EXISTS render_artifact (
  artifact_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dossier_id UUID NOT NULL REFERENCES dossier(dossier_id) ON DELETE CASCADE,
  snapshot_id UUID NOT NULL REFERENCES snapshot(snapshot_id) ON DELETE RESTRICT,
  document_type TEXT NOT NULL,
  lang TEXT NOT NULL CHECK (lang IN ('ar','fr','en')),
  template_id TEXT NOT NULL,
  template_version TEXT NOT NULL,
  policy_id TEXT NOT NULL,
  engine_version TEXT NOT NULL,
  font_manifest_hash TEXT NOT NULL,
  request_key_sha256 TEXT NOT NULL,
  binary_sha256 TEXT NOT NULL,
  storage_uri TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (request_key_sha256)
);

-- 12. Message Queue Outbox (Guaranteed Zero PII)
CREATE TABLE IF NOT EXISTS mq_outbox (
  outbox_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dossier_id UUID NOT NULL REFERENCES dossier(dossier_id) ON DELETE CASCADE,
  payload_json JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  processed_at TIMESTAMPTZ,
  CONSTRAINT mq_payload_minimal_fields_ck CHECK (
    payload_json ? 'dossier_id'
  )
);

-- 13. SQL Guard: Prevent Closed Snapshot Mutation
CREATE OR REPLACE FUNCTION prevent_closed_snapshot_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF old.state = 'CLOTURE' THEN
    RAISE EXCEPTION 'SYNCRA_SECURITY_VIOLATION: Snapshot clôturé: mutation interdite';
  END IF;
  RETURN new;
END;
$$;

DROP TRIGGER IF EXISTS trg_prevent_closed_snapshot_update ON snapshot;
CREATE TRIGGER trg_prevent_closed_snapshot_update
BEFORE UPDATE OR DELETE ON snapshot
FOR EACH ROW
EXECUTE FUNCTION prevent_closed_snapshot_mutation();

-- 14. SQL Guard: Prevent Invalid Cycle Close
CREATE OR REPLACE FUNCTION prevent_invalid_cycle_close()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  v_exists boolean;
BEGIN
  IF new.state = 'CLOTURE' AND old.state <> 'CLOTURE' THEN
    SELECT EXISTS (
      SELECT 1 FROM snapshot s
      WHERE s.cycle_id = new.cycle_id
        AND s.state = 'CLOTURE'
    ) INTO v_exists;

    IF NOT v_exists THEN
      RAISE EXCEPTION 'SYNCRA_INTEGRITY_VIOLATION: Clôture interdite: aucun snapshot clôturé associé';
    END IF;
  END IF;
  RETURN new;
END;
$$;

DROP TRIGGER IF EXISTS trg_prevent_invalid_cycle_close ON payroll_cycle;
CREATE TRIGGER trg_prevent_invalid_cycle_close
BEFORE UPDATE ON payroll_cycle
FOR EACH ROW
EXECUTE FUNCTION prevent_invalid_cycle_close();

-- 15. View: Executable Rules (Only approved and authorized rules can be executed)
CREATE OR REPLACE VIEW v_rules_executable AS
SELECT *
FROM rule_registry
WHERE implementation_autorisee = true
  AND status = 'VALIDE_HORS_PRODUCTION';

-- 16. Seed Initial 14 Calculation Matrix (All Blocked or Conditional Candidates)
INSERT INTO rule_registry (code, label, status, implementation_autorisee, notes) VALUES
('CALC_01_BASE_SALAIRE', 'Salaire de base', 'BLOQUE', false, 'Formule absente'),
('CALC_02_ABS_DED', 'Absences et déductions', 'BLOQUE', false, 'Formule absente'),
('CALC_03_ANC_IEG', 'Ancienneté / IEG', 'BLOQUE', false, 'Barème absent'),
('CALC_04_HS', 'Heures supplémentaires', 'BLOQUE', false, 'Règles absentes'),
('CALC_05_ASSIETTE_SS', 'Assiette SS', 'BLOQUE', false, 'Rubriques et assiette non qualifiées'),
('CALC_06_SS_SAL', 'SS salariale', 'CIBLE_CONDITIONNELLE', false, 'Cible 9% sous réserve N1, assiette et arrondi'),
('CALC_07_SS_PAT', 'SS patronale droit commun', 'CIBLE_CONDITIONNELLE', false, 'Cible 25% sous réserve N1, assiette et arrondi'),
('CALC_08_SS_PAT_ANEM', 'SS patronale ANEM', 'CIBLE_CONDITIONNELLE', false, 'Dépend d une décision CNAS valide'),
('CALC_09_ASSIETTE_IRG', 'Assiette imposable IRG', 'BLOQUE', false, 'Formule absente'),
('CALC_10_IRG_COURANT', 'IRG courant', 'BLOQUE', false, 'Algorithme complet absent'),
('CALC_11_IRG_RAPPELS', 'IRG rappels', 'BLOQUE', false, 'Qualification et algorithme à valider'),
('CALC_12_CONGES', 'Congés et indemnité', 'BLOQUE', false, 'Formules absentes'),
('CALC_13_STC', 'STC', 'BLOQUE', false, 'Règles absentes'),
('CALC_14_NET_COUT', 'Net à payer et coût employeur', 'BLOQUE', false, 'Dépendances, formules et traitement FOS absents')
ON CONFLICT (code) DO NOTHING;

-- 17. Rule Formula Candidate Storage (Inactive Candidates - Not Executed)
CREATE TABLE IF NOT EXISTS rule_formula_candidate (
  candidate_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rule_id UUID NOT NULL REFERENCES rule_registry(rule_id) ON DELETE CASCADE,
  formula_expression TEXT NOT NULL,
  formula_kind TEXT NOT NULL,
  source_ref TEXT,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  active BOOLEAN NOT NULL DEFAULT false,
  CONSTRAINT rule_formula_candidate_inactive_ck CHECK (active = false)
);

-- 18. Seed Formula Candidates (Stored only, strictly inactive)
INSERT INTO rule_formula_candidate (rule_id, formula_expression, formula_kind, source_ref, notes)
SELECT rule_id,
       'ASSIETTE_SS * 0.09',
       'TARGET_CONDITIONAL',
       'Dossier de transmission v0.1',
       'Sous réserve N1, assiette, arrondi, période et tests'
FROM rule_registry WHERE code = 'CALC_06_SS_SAL'
ON CONFLICT DO NOTHING;

INSERT INTO rule_formula_candidate (rule_id, formula_expression, formula_kind, source_ref, notes)
SELECT rule_id,
       'ASSIETTE_SS * 0.25',
       'TARGET_CONDITIONAL',
       'Dossier de transmission v0.1',
       'Sous réserve N1, assiette, arrondi, période et tests'
FROM rule_registry WHERE code = 'CALC_07_SS_PAT'
ON CONFLICT DO NOTHING;

INSERT INTO rule_formula_candidate (rule_id, formula_expression, formula_kind, source_ref, notes)
SELECT rule_id,
       'ASSIETTE_SS * ANEM_TAUX_EFFECTIF',
       'TARGET_CONDITIONAL',
       'Dossier de transmission v0.1',
       'Applicable seulement si décision CNAS validée'
FROM rule_registry WHERE code = 'CALC_08_SS_PAT_ANEM'
ON CONFLICT DO NOTHING;
