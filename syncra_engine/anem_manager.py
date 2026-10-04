"""
SYNCRA ANEM & CNAS Decision Management Module
Tracks ANEM subsidy decisions, validity periods, regional rates,
and detects divergences (ANOMALIE_ANEM_DIVERGENCE).
Handles end-of-contract events (fin_relation_travail) requiring CNAS notification.
"""

from datetime import date
from typing import Dict, Any, Optional
from decimal import Decimal
from .diagnostic_errors import (
    SyncraException,
    SyncraRegulatoryConflictException
)


class AnemDecision:
    def __init__(
        self,
        decision_id: str,
        dossier_id: str,
        employee_id: str,
        decision_number: str,
        effective_rate: Decimal,
        valid_from: date,
        valid_to: date,
        is_cnas_verified: bool = False,
        sector_category: str = "GENERAL",
        notes: Optional[str] = None
    ):
        self.decision_id = decision_id
        self.dossier_id = dossier_id
        self.employee_id = employee_id
        self.decision_number = decision_number
        self.effective_rate = effective_rate
        self.valid_from = valid_from
        self.valid_to = valid_to
        self.is_cnas_verified = is_cnas_verified
        self.sector_category = sector_category
        self.notes = notes

    def is_valid_on(self, period_date: date) -> bool:
        return self.valid_from <= period_date <= self.valid_to


class AnemManager:
    @classmethod
    def validate_anem_application(
        cls,
        decision: Optional[AnemDecision],
        current_period_date: date,
        base_ss_assiette: Decimal
    ) -> Dict[str, Any]:
        """
        Validates whether ANEM employer subsidy applies to the current cycle.
        Emits ANOMALIE_ANEM_DIVERGENCE if expired, unverified, or conflicting.
        """
        if not decision:
            raise SyncraRegulatoryConflictException(
                code="ANOMALIE_ANEM_DIVERGENCE",
                message="Golden Rule Violation: ANEM subsidy claimed but no registered decision found.",
                details={"period": current_period_date.isoformat()}
            )

        if not decision.is_cnas_verified:
            raise SyncraRegulatoryConflictException(
                code="ANOMALIE_ANEM_DIVERGENCE",
                message=f"ANEM Decision '{decision.decision_number}' lacks mandatory CNAS verification visa.",
                details={"decision_id": decision.decision_id}
            )

        if not decision.is_valid_on(current_period_date):
            raise SyncraRegulatoryConflictException(
                code="ANOMALIE_ANEM_DIVERGENCE",
                message=f"ANEM Decision '{decision.decision_number}' is outside validity period ({decision.valid_from} -> {decision.valid_to}).",
                details={
                    "decision_number": decision.decision_number,
                    "period_date": current_period_date.isoformat(),
                    "valid_from": decision.valid_from.isoformat(),
                    "valid_to": decision.valid_to.isoformat()
                }
            )

        # Calculate effective employer contribution under ANEM
        effective_charge = (base_ss_assiette * decision.effective_rate).quantize(Decimal("0.01"))
        standard_charge = (base_ss_assiette * Decimal("0.25")).quantize(Decimal("0.01"))
        abatement_amount = standard_charge - effective_charge

        return {
            "decision_number": decision.decision_number,
            "effective_rate": decision.effective_rate,
            "effective_charge": effective_charge,
            "standard_charge": standard_charge,
            "abatement_amount": abatement_amount,
            "status": "VALID_ANEM_APPLIED"
        }

    @classmethod
    def record_contract_termination_event(
        cls,
        dossier_id: str,
        employee_id: str,
        termination_date: date,
        reason: str
    ) -> Dict[str, Any]:
        """
        Records end of employment relationship (fin de relation de travail).
        Enforces conservative alert: CNAS declaration notification required
        without automating speculative penalties.
        """
        return {
            "event": "FIN_RELATION_TRAVAIL",
            "dossier_id": dossier_id,
            "employee_id": employee_id,
            "termination_date": termination_date.isoformat(),
            "reason": reason,
            "cnas_notification_required": True,
            "notice": "Avis conservatoire: Enregistrement effectué. Déclaration CNAS requise sous les délais réglementaires."
        }

    @classmethod
    def validate_anem_decision_eligibility(
        cls,
        decision_dict: Dict[str, Any],
        calculation_date: str
    ) -> bool:
        """
        Validates whether a decision dict is valid on calculation_date.
        Raises SyncraRegulatoryConflictException('ANOMALIE_ANEM_DIVERGENCE') if expired.
        """
        calc_dt = date.fromisoformat(calculation_date)
        valid_from = date.fromisoformat(decision_dict["valid_from"])
        valid_to = date.fromisoformat(decision_dict["valid_to"])
        if not (valid_from <= calc_dt <= valid_to):
            raise SyncraRegulatoryConflictException(
                code="ANOMALIE_ANEM_DIVERGENCE",
                message=f"ANEM decision expired or outside calculation date {calculation_date} (valid {valid_from} to {valid_to}).",
                details=decision_dict
            )
        return True


# Aliases
SyncraAnemManager = AnemManager
