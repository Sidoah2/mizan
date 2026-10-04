"""
SYNCRA The 4 Validation Gates Engine
Implements Gate 1, Gate 2, Gate 3, Gate 4 and the Golden Design Rule (Fail-Fast).
"""

from typing import Dict, Any, List, Set, Optional
from .diagnostic_errors import (
    SyncraGateValidationException,
    SyncraSecurityException,
    SyncraMissingConfigurationException,
    SyncraRegulatoryConflictException
)


class SyncraGatesValidator:
    FORBIDDEN_PII_FIELDS = {
        "nss",
        "employee_name",
        "first_name",
        "last_name",
        "birth_date",
        "bank_rib",
        "phone",
        "email"
    }

    # =========================================================================
    # GATE 1: Legal Accreditation (N1 - Algerian Official Gazette)
    # =========================================================================
    @staticmethod
    def validate_gate_1_rule(rule_data: Dict[str, Any]) -> bool:
        """
        Validates that a rule is legally accredited by official Algerian Gazette (N1).
        If implementation_autorisee is False or status is not VALIDE_HORS_PRODUCTION,
        execution MUST be rejected.
        """
        code = rule_data.get("code")
        status = rule_data.get("status")
        auth = rule_data.get("implementation_autorisee", False)
        legal_ref = rule_data.get("legal_source_ref")

        if not auth or status != "VALIDE_HORS_PRODUCTION":
            raise SyncraGateValidationException(
                code="SYNCRA_ERR_UNAUTHORIZED_RULE_EXECUTION",
                message=f"Gate 1 Failed: Rule '{code}' is not legally accredited for production execution.",
                details={"code": code, "status": status, "implementation_autorisee": auth}
            )

        if not legal_ref or not legal_ref.strip():
            raise SyncraGateValidationException(
                code="SYNCRA_ERR_MISSING_LEGAL_SOURCE_N1",
                message=f"Gate 1 Failed: Rule '{code}' is missing mandatory Algerian Official Gazette (N1) reference.",
                details={"code": code}
            )

        return True

    # =========================================================================
    # GATE 2: Tenant Isolation & RBAC
    # =========================================================================
    @staticmethod
    def validate_gate_2_isolation(
        current_user_dossier_id: str,
        target_resource_dossier_id: str,
        user_role: str,
        allowed_roles: List[str]
    ) -> bool:
        """
        Validates strict dossier isolation and Role-Based Access Control (RBAC).
        Rejects any cross-dossier queries immediately.
        """
        if current_user_dossier_id != target_resource_dossier_id:
            raise SyncraSecurityException(
                code="SYNCRA_ERR_CROSS_DOSSIER_ACCESS",
                message="Gate 2 Failed: Cross-dossier access violation detected. Access rejected.",
                details={
                    "caller_dossier_id": current_user_dossier_id,
                    "target_dossier_id": target_resource_dossier_id
                }
            )

        if user_role not in allowed_roles:
            raise SyncraSecurityException(
                code="SYNCRA_ERR_RBAC_UNAUTHORIZED",
                message=f"Gate 2 Failed: User role '{user_role}' is not authorized for this operation.",
                details={"user_role": user_role, "allowed_roles": allowed_roles}
            )

        return True

    # =========================================================================
    # GATE 3: Zero PII in MQ & Localization Completeness
    # =========================================================================
    @classmethod
    def validate_gate_3_mq_payload(cls, payload: Dict[str, Any]) -> bool:
        """
        Ensures that MQ messages carry ZERO personally identifiable information (PII).
        Only technical UUIDs and event codes are allowed.
        """
        payload_keys = set(payload.keys())
        leaked_fields = payload_keys.intersection(cls.FORBIDDEN_PII_FIELDS)
        if leaked_fields:
            raise SyncraSecurityException(
                code="SYNCRA_ERR_PII_LEAK_IN_MQ",
                message=f"Gate 3 Failed: Forbidden PII fields detected in MQ payload: {list(leaked_fields)}.",
                details={"leaked_fields": list(leaked_fields)}
            )

        if "dossier_id" not in payload:
            raise SyncraGateValidationException(
                code="SYNCRA_ERR_MQ_MISSING_DOSSIER_ID",
                message="Gate 3 Failed: MQ payload must contain 'dossier_id' technical key."
            )

        return True

    @staticmethod
    def validate_gate_3_label_completeness(
        label_code: str,
        available_translations: Dict[str, str],
        required_languages: Set[str] = None
    ) -> bool:
        """
        Ensures that every label is translated in all required languages (ar, fr, en).
        Fail-Fast on any missing translation.
        """
        if required_languages is None:
            required_languages = {"ar", "fr", "en"}

        missing = required_languages - set(available_translations.keys())
        if missing:
            raise SyncraMissingConfigurationException(
                code="SYNCRA_ERR_LABEL_MISSING_TRANSLATION",
                message=f"Gate 3 Failed: Label '{label_code}' is missing translations for: {list(missing)}.",
                details={"label_code": label_code, "missing_languages": list(missing)}
            )

        return True

    # =========================================================================
    # GATE 4: Golden Tests & Determinism Verification
    # =========================================================================
    @staticmethod
    def validate_gate_4_determinism(actual_hash: str, expected_golden_hash: str) -> bool:
        """
        Validates that calculation output matches expected golden test baseline bit-for-bit.
        """
        if actual_hash != expected_golden_hash:
            raise SyncraGateValidationException(
                code="SYNCRA_ERR_GOLDEN_REGRESSION_MISMATCH",
                message="Gate 4 Failed: Calculation hash diverges from golden test baseline. Potential regression.",
                details={"actual_hash": actual_hash, "expected_hash": expected_golden_hash}
            )
        return True

    # =========================================================================
    # GOLDEN DESIGN RULE: Never Assume (Fail-Fast Checks)
    # =========================================================================
    @staticmethod
    def validate_rounding_policy(rounding_config: Optional[Dict[str, Any]]) -> bool:
        """
        Fails fast if rounding policy is missing or ambiguous.
        Never assume half-up, truncation, or currency rounding.
        """
        if not rounding_config:
            raise SyncraMissingConfigurationException(
                code="SYNCRA_ERR_ROUNDING_POLICY_MISSING",
                message="Golden Rule Violation: Rounding policy is missing. Cannot proceed with heuristic rounding."
            )

        policy = rounding_config.get("policy")
        precision = rounding_config.get("precision")
        if not policy or precision is None:
            raise SyncraMissingConfigurationException(
                code="SYNCRA_ERR_ROUNDING_POLICY_INCOMPLETE",
                message="Golden Rule Violation: Incomplete rounding policy specification.",
                details=rounding_config
            )

        return True

    @staticmethod
    def validate_anem_decision(decision: Optional[Dict[str, Any]], current_period_date: str) -> bool:
        """
        Validates ANEM decision validity and detects regulatory expiration or conflicts.
        """
        if not decision:
            raise SyncraRegulatoryConflictException(
                code="SYNCRA_ERR_ANEM_DECISION_MISSING",
                message="Golden Rule Violation: ANEM decision is missing for contract with ANEM subsidy rate."
            )

        is_valid = decision.get("is_valid_cnas", False)
        expiry_date = decision.get("expiry_date")
        if not is_valid or (expiry_date and current_period_date > expiry_date):
            raise SyncraRegulatoryConflictException(
                code="SYNCRA_ERR_REGULATORY_CONFLICT_ANEM",
                message="Golden Rule Violation: ANEM decision is invalid or expired. Calculation halted.",
                details={"decision_id": decision.get("id"), "expiry": expiry_date, "period": current_period_date}
            )

        return True
