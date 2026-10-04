# MIZAN — Scripts de base de données et calculs de base

**Version:** extrait de travail à partir des pièces jointes fournies uniquement.  
**Principe:** ce document ne crée **aucune règle de paie nouvelle**, ne propose **aucun schéma implicite**, et ne transforme **aucune cible métier** en règle exécutable de production tant que les validations prévues ne sont pas closes. [cite:1][cite:2]

## Portée

Le dossier source autorise la conception de l’architecture et des tests sur données synthétiques, mais interdit d’activer une règle métier ou d’émettre un résultat réglementaire sur la seule foi de ces documents. [cite:1][cite:2]

Les noms d’objets décrivent des responsabilités et des invariants, **pas** des tables SQL ni des API déjà approuvées. En conséquence, ce livrable fournit des **scripts de base minimaux**, orientés socle technique, traçabilité, gel, versionnement, isolation et blocage explicite des règles non validées. [cite:1][cite:2]

## Contraintes non négociables

- Bitemporalité obligatoire pour les données métier et paramètres versionnés: conservation du **valid time** et du **transaction time**. [cite:1][cite:2]
- États métier retenus: `SAISIE -> EN_CALCUL -> CLOTURE`, avec retour explicite `EN_CALCUL -> SAISIE` uniquement pour correction puis nouveau gel. [cite:1][cite:2]
- Un snapshot clôturé est en lecture seule et ne peut pas être réécrit. [cite:1][cite:2]
- Le moteur doit être déterministe, versionné, traçable, et ne pas utiliser de `float` binaire pour fixer des montants de paie. [cite:1][cite:2]
- Une fiche non close peut être enregistrée avec `implementation_autorisee=false` et doit être refusée par le moteur de production. [cite:1][cite:2]
- Aucune PII ne doit être transportée dans MQ; seuls des identifiants techniques sont admis. [cite:1][cite:2]

## Position sur les calculs

Les documents distinguent clairement trois niveaux:

1. **Calculs bloqués**: formule absente, barème absent, assiette non qualifiée ou algorithme incomplet. [cite:1][cite:2]
2. **Formules cibles conditionnelles**: utiles pour préparer le moteur, mais non activables en production sans validation complète N1, assiette, arrondis, période et tests. [cite:1][cite:2]
3. **Exemples illustratifs**: simples cas de test explicatifs, sans valeur de validation métier. [cite:1][cite:2]

## Matrice des 14 postes

| ID | Objet | Statut |
|---|---|---|
| 01 | Salaire de base | Bloqué: formule absente. [cite:1][cite:2] |
| 02 | Absences et déductions | Bloqué: formule absente. [cite:1][cite:2] |
| 03 | Ancienneté / IEG | Bloqué: barème absent. [cite:1][cite:2] |
| 04 | Heures supplémentaires | Bloqué: règles absentes. [cite:1][cite:2] |
| 05 | Assiette SS | Bloqué: rubriques et assiette non qualifiées. [cite:1][cite:2] |
| 06 | SS salariale | Cible 9 %, sous réserve N1, assiette et arrondi. [cite:1][cite:2] |
| 07 | SS patronale droit commun | Cible 25 %, sous réserve N1, assiette et arrondi. [cite:1][cite:2] |
| 08 | SS patronale ANEM | Cible dépendante d’une décision CNAS; chaîne juridique et conditions non closes. [cite:1][cite:2] |
| 09 | Assiette imposable IRG | Bloqué: formule absente. [cite:1][cite:2] |
| 10 | IRG courant | Bloqué: algorithme complet absent. [cite:1][cite:2] |
| 11 | IRG rappels | Bloqué: qualification et algorithme à valider. [cite:1][cite:2] |
| 12 | Congés et indemnité | Bloqué: formules absentes. [cite:1][cite:2] |
| 13 | STC | Bloqué: règles absentes. [cite:1][cite:2] |
| 14 | Net à payer et coût employeur | Bloqué: dépendances, formules et traitement FOS absents. [cite:1][cite:2] |

## Formules explicitement présentes mais non activées

Les seules formules écrites explicitement dans les pièces sont les suivantes, toutes soumises à validation juridique, assiette, arrondis, période d’effet et tests dorés avant toute activation. [cite:1][cite:2]

- `CALC_06_SS_SAL = ASSIETTE_SS × 0,09` [cite:1][cite:2]
- `CALC_07_SS_PAT = ASSIETTE_SS × 0,25` [cite:1][cite:2]
- `CALC_08_SS_PAT_ANEM = ASSIETTE_SS × ANEM_TAUX_EFFECTIF` si la décision applicable est validée. [cite:1][cite:2]
- `ABATTEMENT_PATRONAL_MONTANT = (ASSIETTE_SS × taux patronal de référence applicable) − CHARGE_SS_PAT_EFFECTIVE` comme formule cible conditionnelle, non activée. [cite:1][cite:2]

Le cas numérique `ASSIETTE_SS = 50 000 DZD` avec un taux effectif de 5 % n’est donné que comme illustration de test: 4 500 salarié, 12 500 employeur de référence, 2 500 effectif, écart 10 000. Cet exemple ne valide ni l’assiette ni les arrondis. [cite:1]

## Scripts SQL de socle

Les scripts ci-dessous sont volontairement limités à un **socle technique compatible avec les contraintes documentées**. Les détails de stack, types exacts, partitions, chiffrement, APIs, moteurs et fournisseurs restent hors périmètre dans les pièces. [cite:1][cite:2]

```sql
-- 00_extensions.sql
-- Choix minimal pour UUID et hachage; à adapter à la stack approuvée.
create extension if not exists pgcrypto;
```

```sql
-- 01_enums.sql
create type cycle_state as enum ('SAISIE', 'EN_CALCUL', 'CLOTURE');

create type rule_status as enum (
  'EN_ATTENTE_N1',
  'BLOQUE',
  'A_DOCUMENTER',
  'A_ARBITRER',
  'CIBLE_CONDITIONNELLE',
  'VALIDE_HORS_PRODUCTION'
);
```

```sql
-- 02_dossiers.sql
create table dossier (
  dossier_id uuid primary key default gen_random_uuid(),
  code text not null unique,
  created_at timestamptz not null default now()
);
```

```sql
-- 03_cycles.sql
create table payroll_cycle (
  cycle_id uuid primary key default gen_random_uuid(),
  dossier_id uuid not null references dossier(dossier_id),
  employee_id uuid not null,
  period_start date not null,
  period_end date not null,
  state cycle_state not null default 'SAISIE',
  current_manifest_hash text,
  created_at timestamptz not null default now(),
  closed_at timestamptz,
  constraint payroll_cycle_period_ck check (period_end >= period_start)
);

create index payroll_cycle_dossier_idx on payroll_cycle(dossier_id);
create index payroll_cycle_employee_idx on payroll_cycle(employee_id);
```

```sql
-- 04_bitemporal_values.sql
create table bitemporal_value (
  value_id uuid primary key default gen_random_uuid(),
  dossier_id uuid not null references dossier(dossier_id),
  scope_type text not null,
  scope_id uuid not null,
  field_code text not null,
  value_json jsonb not null,
  valid_from date not null,
  valid_to date,
  tx_from timestamptz not null default now(),
  tx_to timestamptz,
  source_ref text,
  created_by text,
  constraint bitemporal_valid_range_ck check (valid_to is null or valid_to >= valid_from),
  constraint bitemporal_tx_range_ck check (tx_to is null or tx_to >= tx_from)
);

create index bitemporal_scope_idx on bitemporal_value(dossier_id, scope_type, scope_id, field_code);
create index bitemporal_valid_idx on bitemporal_value(valid_from, valid_to);
create index bitemporal_tx_idx on bitemporal_value(tx_from, tx_to);
```

```sql
-- 05_rule_registry.sql
create table rule_registry (
  rule_id uuid primary key default gen_random_uuid(),
  code text not null unique,
  label text not null,
  status rule_status not null,
  implementation_autorisee boolean not null default false,
  ast_version text,
  legal_source_ref text,
  legal_article_ref text,
  valid_from date,
  valid_to date,
  notes text,
  created_at timestamptz not null default now(),
  constraint rule_no_prod_without_flag_ck check (
    (implementation_autorisee = false)
    or (status in ('VALIDE_HORS_PRODUCTION'))
  )
);
```

```sql
-- 06_rule_dependencies.sql
create table rule_dependency (
  rule_id uuid not null references rule_registry(rule_id) on delete cascade,
  depends_on_rule_id uuid not null references rule_registry(rule_id) on delete restrict,
  primary key (rule_id, depends_on_rule_id),
  constraint rule_dependency_no_self_ck check (rule_id <> depends_on_rule_id)
);
```

```sql
-- 07_manifests_and_snapshots.sql
create table manifest (
  manifest_id uuid primary key default gen_random_uuid(),
  cycle_id uuid not null references payroll_cycle(cycle_id),
  dossier_id uuid not null references dossier(dossier_id),
  manifest_json jsonb not null,
  manifest_hash text not null,
  created_at timestamptz not null default now()
);

create unique index manifest_hash_uq on manifest(manifest_hash);
create index manifest_cycle_idx on manifest(cycle_id);

create table snapshot (
  snapshot_id uuid primary key default gen_random_uuid(),
  cycle_id uuid not null references payroll_cycle(cycle_id),
  dossier_id uuid not null references dossier(dossier_id),
  manifest_id uuid not null references manifest(manifest_id),
  snapshot_json jsonb not null,
  snapshot_hash text not null,
  state cycle_state not null,
  created_at timestamptz not null default now(),
  closed_at timestamptz,
  constraint snapshot_state_ck check (state in ('EN_CALCUL', 'CLOTURE'))
);

create unique index snapshot_hash_uq on snapshot(snapshot_hash);
create index snapshot_cycle_idx on snapshot(cycle_id);
```

```sql
-- 08_attempts.sql
create table calc_attempt (
  attempt_id uuid primary key default gen_random_uuid(),
  cycle_id uuid not null references payroll_cycle(cycle_id),
  dossier_id uuid not null references dossier(dossier_id),
  manifest_id uuid not null references manifest(manifest_id),
  snapshot_id uuid references snapshot(snapshot_id),
  engine_version text not null,
  status text not null,
  diagnostics_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index calc_attempt_cycle_idx on calc_attempt(cycle_id);
create index calc_attempt_dossier_idx on calc_attempt(dossier_id);
```

```sql
-- 09_rule_execution_trace.sql
create table rule_execution_trace (
  trace_id uuid primary key default gen_random_uuid(),
  attempt_id uuid not null references calc_attempt(attempt_id) on delete cascade,
  rule_id uuid not null references rule_registry(rule_id),
  input_json jsonb,
  output_json jsonb,
  anomaly_code text,
  created_at timestamptz not null default now()
);

create index rule_execution_attempt_idx on rule_execution_trace(attempt_id);
create index rule_execution_rule_idx on rule_execution_trace(rule_id);
```

```sql
-- 10_labels.sql
create table data_label_catalog (
  label_id uuid primary key default gen_random_uuid(),
  dossier_id uuid references dossier(dossier_id),
  label_code text not null,
  lang text not null,
  label_value text not null,
  valid_from date,
  valid_to date,
  tx_from timestamptz not null default now(),
  tx_to timestamptz,
  constraint data_label_lang_ck check (lang in ('ar', 'fr', 'en'))
);

create unique index data_label_catalog_uq
  on data_label_catalog(coalesce(dossier_id, '00000000-0000-0000-0000-000000000000'::uuid), label_code, lang, tx_from);
```

```sql
-- 11_render_artifacts.sql
create table render_artifact (
  artifact_id uuid primary key default gen_random_uuid(),
  dossier_id uuid not null references dossier(dossier_id),
  snapshot_id uuid not null references snapshot(snapshot_id),
  document_type text not null,
  lang text not null check (lang in ('ar','fr','en')),
  template_id text not null,
  template_version text not null,
  policy_id text not null,
  engine_version text not null,
  font_manifest_hash text not null,
  request_key_sha256 text not null,
  binary_sha256 text not null,
  created_at timestamptz not null default now(),
  unique (request_key_sha256)
);
```

```sql
-- 12_mq_payload_outbox.sql
create table mq_outbox (
  outbox_id uuid primary key default gen_random_uuid(),
  dossier_id uuid not null references dossier(dossier_id),
  payload_json jsonb not null,
  created_at timestamptz not null default now(),
  processed_at timestamptz,
  constraint mq_payload_minimal_fields_ck check (
    payload_json ? 'dossier_id'
  )
);
```

## Garde-fous SQL minimaux

```sql
-- 13_prevent_closed_snapshot_update.sql
create or replace function prevent_closed_snapshot_mutation()
returns trigger
language plpgsql
as $$
begin
  if old.state = 'CLOTURE' then
    raise exception 'Snapshot clôturé: mutation interdite';
  end if;
  return new;
end;
$$;

create trigger trg_prevent_closed_snapshot_update
before update on snapshot
for each row
execute function prevent_closed_snapshot_mutation();
```

```sql
-- 14_prevent_cycle_close_without_snapshot.sql
create or replace function prevent_invalid_cycle_close()
returns trigger
language plpgsql
as $$
declare
  v_exists boolean;
begin
  if new.state = 'CLOTURE' and old.state <> 'CLOTURE' then
    select exists (
      select 1 from snapshot s
      where s.cycle_id = new.cycle_id
        and s.state = 'CLOTURE'
    ) into v_exists;

    if not v_exists then
      raise exception 'Clôture interdite: aucun snapshot clôturé associé';
    end if;
  end if;
  return new;
end;
$$;

create trigger trg_prevent_invalid_cycle_close
before update on payroll_cycle
for each row
execute function prevent_invalid_cycle_close();
```

```sql
-- 15_block_non_authorized_rules.sql
create or replace view v_rules_executable as
select *
from rule_registry
where implementation_autorisee = true
  and status = 'VALIDE_HORS_PRODUCTION';
```

## Enregistrements de base du registre de calcul

```sql
-- 16_seed_rule_registry.sql
insert into rule_registry (code, label, status, implementation_autorisee, notes) values
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
('CALC_14_NET_COUT', 'Net à payer et coût employeur', 'BLOQUE', false, 'Dépendances, formules et traitement FOS absents');
```

## Expressions de calcul à stocker, pas à activer

Les pièces justifient la préparation d’un stockage déclaratif des expressions, mais pas leur activation automatique. [cite:1][cite:2]

```sql
-- 17_rule_formula_storage.sql
create table rule_formula_candidate (
  candidate_id uuid primary key default gen_random_uuid(),
  rule_id uuid not null references rule_registry(rule_id) on delete cascade,
  formula_expression text not null,
  formula_kind text not null,
  source_ref text,
  notes text,
  created_at timestamptz not null default now(),
  active boolean not null default false,
  constraint rule_formula_candidate_inactive_ck check (active = false)
);
```

```sql
-- 18_seed_formula_candidates.sql
insert into rule_formula_candidate (rule_id, formula_expression, formula_kind, source_ref, notes)
select rule_id,
       'ASSIETTE_SS * 0.09',
       'TARGET_CONDITIONAL',
       'Dossier de transmission v0.1',
       'Sous réserve N1, assiette, arrondi, période et tests'
from rule_registry where code = 'CALC_06_SS_SAL';

insert into rule_formula_candidate (rule_id, formula_expression, formula_kind, source_ref, notes)
select rule_id,
       'ASSIETTE_SS * 0.25',
       'TARGET_CONDITIONAL',
       'Dossier de transmission v0.1',
       'Sous réserve N1, assiette, arrondi, période et tests'
from rule_registry where code = 'CALC_07_SS_PAT';

insert into rule_formula_candidate (rule_id, formula_expression, formula_kind, source_ref, notes)
select rule_id,
       'ASSIETTE_SS * ANEM_TAUX_EFFECTIF',
       'TARGET_CONDITIONAL',
       'Dossier de transmission v0.1',
       'Applicable seulement si décision CNAS validée'
from rule_registry where code = 'CALC_08_SS_PAT_ANEM';

insert into rule_formula_candidate (rule_id, formula_expression, formula_kind, source_ref, notes)
select rule_id,
       '(ASSIETTE_SS * TAUX_PATRONAL_REFERENCE) - CHARGE_SS_PAT_EFFECTIVE',
       'TARGET_CONDITIONAL',
       'Dossier de transmission v0.1',
       'Abattement patronal montant; formule cible conditionnelle, non activée'
from rule_registry where code = 'CALC_07_SS_PAT';
```

## Ce que ces scripts ne font pas volontairement

- Ils ne définissent pas l’algorithme IRG courant ni IRG rappels. [cite:1][cite:2]
- Ils ne définissent pas l’assiette SS ni l’assiette imposable IRG. [cite:1][cite:2]
- Ils ne définissent pas les arrondis métier. [cite:1][cite:2]
- Ils ne définissent pas les rubriques, barèmes, congés, STC, heures supplémentaires ou FOS. [cite:1][cite:2]
- Ils ne choisissent ni Supabase, ni moteur PDF, ni format exact d’API, ni politique de clés, ni hébergeur. [cite:1][cite:2]
- Ils ne rendent aucune règle exécutable en production. [cite:1][cite:2]

## Conditions avant extension

Avant d’ajouter la moindre formule active ou de compléter le schéma métier détaillé, les documents exigent la clôture des points suivants: source N1 applicable, assiettes qualifiées, dépendances définies, politique d’arrondi, période d’effet, golden tests, contrôles d’accès et décisions métier/juridiques correspondantes. [cite:1][cite:2]

Tant que ces éléments ne sont pas fournis, la seule posture sûre consiste à préparer le **socle de stockage, de gel, de traçabilité et de blocage**, puis à faire remonter chaque manque comme question explicite au lieu de le compléter par intuition. [cite:1][cite:2]
