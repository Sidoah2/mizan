-- =====================================================================
-- SYNCRA Migration: ANEM Decisions, Render Artifacts & Conflict Registry
-- Compliance: Gate 1 Legal Accreditation, Article 86 Law 90-11,
--             Ordonnance 95-01, and Rendering Immutability
-- Version: 1.1.0 (October 2026)
-- =====================================================================

-- 01. ANEM Employment Subsidy Decisions
CREATE TABLE IF NOT EXISTS anem_decision (
  decision_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dossier_id UUID NOT NULL REFERENCES dossier(dossier_id) ON DELETE CASCADE,
  employee_id UUID NOT NULL,
  decision_number TEXT NOT NULL,
  device_code TEXT NOT NULL, -- e.g., CTA_DEVELOPPEMENT, DAIP, HANDICAP
  effective_rate NUMERIC(5,4) NOT NULL, -- e.g., 0.5000 for 50% abatement
  valid_from DATE NOT NULL,
  valid_to DATE NOT NULL,
  is_cnas_verified BOOLEAN NOT NULL DEFAULT false,
  sector_category TEXT NOT NULL DEFAULT 'GENERAL',
  official_doc_reference TEXT,
  metadata_json JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT anem_validity_ck CHECK (valid_to >= valid_from),
  CONSTRAINT anem_rate_ck CHECK (effective_rate >= 0.0000 AND effective_rate <= 1.0000)
);

CREATE INDEX IF NOT EXISTS anem_decision_lookup_idx 
  ON anem_decision(dossier_id, employee_id, valid_from, valid_to);

-- 02. Contract Termination Events (Fin de relation de travail)
CREATE TABLE IF NOT EXISTS contract_termination_event (
  event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dossier_id UUID NOT NULL REFERENCES dossier(dossier_id) ON DELETE CASCADE,
  employee_id UUID NOT NULL,
  termination_date DATE NOT NULL,
  reason TEXT NOT NULL,
  cnas_notification_required BOOLEAN NOT NULL DEFAULT true,
  cnas_declared_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS termination_event_dossier_idx 
  ON contract_termination_event(dossier_id, employee_id);

-- 03. Render Artifacts & Frozen Documents (Article 86 Compliance)
CREATE TABLE IF NOT EXISTS render_artifact (
  artifact_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dossier_id UUID NOT NULL REFERENCES dossier(dossier_id) ON DELETE CASCADE,
  snapshot_id UUID NOT NULL REFERENCES calculation_snapshot(snapshot_id) ON DELETE RESTRICT,
  request_key_sha256 TEXT NOT NULL UNIQUE,
  binary_sha256 TEXT NOT NULL,
  document_type TEXT NOT NULL DEFAULT 'BULLETIN_DE_PAIE',
  lang TEXT NOT NULL CHECK (lang IN ('ar', 'fr')),
  template_id TEXT NOT NULL,
  template_version TEXT NOT NULL,
  engine_version TEXT NOT NULL,
  font_manifest_hash TEXT NOT NULL,
  payload_json JSONB NOT NULL,
  status TEXT NOT NULL DEFAULT 'RENDER_SEALED',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS render_artifact_req_idx ON render_artifact(request_key_sha256);
CREATE INDEX IF NOT EXISTS render_artifact_snapshot_idx ON render_artifact(snapshot_id);

-- Immutable Trigger on render_artifact
CREATE OR REPLACE FUNCTION prevent_render_artifact_mutation()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'SYNCRA_SECURITY_VIOLATION: Rendered artifacts are strictly immutable once sealed (request_key: %).', OLD.request_key_sha256;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_prevent_render_artifact_mutation ON render_artifact;
CREATE TRIGGER trg_prevent_render_artifact_mutation
  BEFORE UPDATE OR DELETE ON render_artifact
  FOR EACH ROW
  EXECUTE FUNCTION prevent_render_artifact_mutation();

-- 04. Regulatory Conflict & Discrepancy Log (Audit Trail)
CREATE TABLE IF NOT EXISTS regulatory_conflict_log (
  conflict_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rule_code TEXT NOT NULL,
  source_a TEXT NOT NULL,
  source_b TEXT NOT NULL,
  divergence_description TEXT NOT NULL,
  potential_impact TEXT,
  resolution_status TEXT NOT NULL DEFAULT 'PENDING_OFFICIAL_ARBITRATION',
  resolution_authority TEXT,
  resolution_reference TEXT,
  reported_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS regulatory_conflict_rule_idx ON regulatory_conflict_log(rule_code, resolution_status);
