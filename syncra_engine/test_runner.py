"""
SYNCRA Automated Test Suite & Negative Tests Runner
Runs both positive validation and negative fail-fast tests across all engine components.
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
from decimal import Decimal
from syncra_engine.diagnostic_errors import (
    SyncraException,
    SyncraSecurityException,
    SyncraGateValidationException,
    SyncraMissingConfigurationException,
    SyncraRegulatoryConflictException
)
from syncra_engine.idempotency import SyncraIdempotencyService
from syncra_engine.lifecycle import PayrollCycle, Snapshot, CycleState
from syncra_engine.gates import SyncraGatesValidator


def run_all_tests():
    passed = 0
    failed = 0

    print("=" * 70)
    print("🚀 STARTING SYNCRA AUTOMATED ENGINE TESTS & VALIDATION GATES")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # TEST 1: Idempotency Key Determinism
    # -------------------------------------------------------------------------
    try:
        key1 = SyncraIdempotencyService.compute_render_idempotency_key(
            dossier_id="dossier-001",
            snapshot_id="snapshot-999",
            document_type="PAYSLIP",
            lang="ar",
            template_id="std_v1",
            template_version="1.0.0",
            policy_id="DZ_2026",
            engine_version="1.0.0",
            font_manifest_hash="cairo_hash_123"
        )
        key2 = SyncraIdempotencyService.compute_render_idempotency_key(
            dossier_id="dossier-001",
            snapshot_id="snapshot-999",
            document_type="PAYSLIP",
            lang="ar",
            template_id="std_v1",
            template_version="1.0.0",
            policy_id="DZ_2026",
            engine_version="1.0.0",
            font_manifest_hash="cairo_hash_123"
        )
        assert key1 == key2, "Idempotency keys must be strictly identical for identical inputs."
        print(f"✔ TEST 1 PASSED: Idempotency Key Determinism Verified ({key1[:16]}...)")
        passed += 1
    except Exception as e:
        print(f"❌ TEST 1 FAILED: {e}")
        failed += 1

    # -------------------------------------------------------------------------
    # TEST 2: Lifecycle Transitions (SAISIE -> EN_CALCUL -> CLOTURE)
    # -------------------------------------------------------------------------
    try:
        cycle = PayrollCycle("cycle-101", "dossier-001", "emp-555", "2026-10-01", "2026-10-31")
        assert cycle.state == CycleState.SAISIE
        
        manifest = cycle.freeze_for_calculation({"base_hours": 173.33, "deductions": 0})
        assert cycle.state == CycleState.EN_CALCUL
        assert manifest.manifest_hash is not None

        snapshot = Snapshot(cycle.cycle_id, cycle.dossier_id, manifest.manifest_id, {"gross": Decimal("100000.00")})
        cycle.close_cycle(snapshot)
        assert cycle.state == CycleState.CLOTURE
        assert snapshot.state == CycleState.CLOTURE
        print("✔ TEST 2 PASSED: 3-State Lifecycle Verified (SAISIE -> EN_CALCUL -> CLOTURE)")
        passed += 1
    except Exception as e:
        print(f"❌ TEST 2 FAILED: {e}")
        failed += 1

    # -------------------------------------------------------------------------
    # TEST 3 (NEGATIVE): Mutating Closed Snapshot Must Raise Security Exception
    # -------------------------------------------------------------------------
    try:
        # snapshot is now sealed under CLOTURE from Test 2
        snapshot.update_results({"net": Decimal("999999.00")})
        print("❌ TEST 3 FAILED: Mutation of closed snapshot was NOT blocked!")
        failed += 1
    except SyncraSecurityException as e:
        print(f"✔ TEST 3 PASSED: Mutating closed snapshot correctly blocked -> [{e.code}]")
        passed += 1
    except Exception as e:
        print(f"❌ TEST 3 FAILED with unexpected exception: {e}")
        failed += 1

    # -------------------------------------------------------------------------
    # TEST 4 (NEGATIVE): Gate 1 - Refusing Unapproved Rule
    # -------------------------------------------------------------------------
    try:
        rule_data = {
            "code": "CALC_01_BASE_SALAIRE",
            "status": "BLOQUE",
            "implementation_autorisee": False,
            "legal_source_ref": None
        }
        SyncraGatesValidator.validate_gate_1_rule(rule_data)
        print("❌ TEST 4 FAILED: Gate 1 allowed an unapproved rule!")
        failed += 1
    except SyncraGateValidationException as e:
        print(f"✔ TEST 4 PASSED: Gate 1 correctly blocked unapproved rule -> [{e.code}]")
        passed += 1

    # -------------------------------------------------------------------------
    # TEST 5 (NEGATIVE): Gate 2 - Cross-Dossier Access Rejection
    # -------------------------------------------------------------------------
    try:
        SyncraGatesValidator.validate_gate_2_isolation(
            current_user_dossier_id="dossier-COMPANY-A",
            target_resource_dossier_id="dossier-COMPANY-B",
            user_role="ACCOUNTANT",
            allowed_roles=["ADMIN", "ACCOUNTANT"]
        )
        print("❌ TEST 5 FAILED: Gate 2 allowed cross-dossier access!")
        failed += 1
    except SyncraSecurityException as e:
        print(f"✔ TEST 5 PASSED: Gate 2 correctly rejected cross-dossier access -> [{e.code}]")
        passed += 1

    # -------------------------------------------------------------------------
    # TEST 6 (NEGATIVE): Gate 3 - Zero PII in MQ Outbox
    # -------------------------------------------------------------------------
    try:
        mq_payload_with_pii = {
            "dossier_id": "dossier-001",
            "event": "PAYROLL_CLOSED",
            "nss": "987654321012",  # FORBIDDEN PII LEAK!
            "employee_name": "Slimane Benali"
        }
        SyncraGatesValidator.validate_gate_3_mq_payload(mq_payload_with_pii)
        print("❌ TEST 6 FAILED: Gate 3 allowed PII in MQ payload!")
        failed += 1
    except SyncraSecurityException as e:
        print(f"✔ TEST 6 PASSED: Gate 3 caught PII leak in MQ payload -> [{e.code}]")
        passed += 1

    # -------------------------------------------------------------------------
    # TEST 7 (NEGATIVE): Gate 3 - Missing Label Translation Fail-Fast
    # -------------------------------------------------------------------------
    try:
        translations = {
            "ar": "الأجر القاعدي",
            "fr": "Salaire de base"
            # "en" is missing!
        }
        SyncraGatesValidator.validate_gate_3_label_completeness("SALAIRE_BASE", translations)
        print("❌ TEST 7 FAILED: Gate 3 did not catch missing English translation!")
        failed += 1
    except SyncraMissingConfigurationException as e:
        print(f"✔ TEST 7 PASSED: Gate 3 halted on missing translation -> [{e.code}]")
        passed += 1

    # -------------------------------------------------------------------------
    # TEST 8 (NEGATIVE): Golden Rule - Missing Rounding Policy
    # -------------------------------------------------------------------------
    try:
        SyncraGatesValidator.validate_rounding_policy(None)
        print("❌ TEST 8 FAILED: Engine proceeded without rounding policy!")
        failed += 1
    except SyncraMissingConfigurationException as e:
        print(f"✔ TEST 8 PASSED: Golden Rule halted on missing rounding policy -> [{e.code}]")
        passed += 1

    # -------------------------------------------------------------------------
    # TEST 9 (NEGATIVE): Golden Rule - Expired ANEM Decision Conflict
    # -------------------------------------------------------------------------
    try:
        expired_decision = {
            "id": "ANEM-DEC-2024-001",
            "is_valid_cnas": True,
            "expiry_date": "2025-12-31"
        }
        SyncraGatesValidator.validate_anem_decision(expired_decision, current_period_date="2026-10-01")
        print("❌ TEST 9 FAILED: Engine accepted an expired ANEM decision!")
        failed += 1
    except SyncraRegulatoryConflictException as e:
        print(f"✔ TEST 9 PASSED: Golden Rule halted on expired ANEM decision -> [{e.code}]")
        passed += 1

    print("=" * 70)
    print(f"🏁 TEST SUMMARY: {passed} PASSED, {failed} FAILED (TOTAL {passed + failed})")
    print("=" * 70)
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
