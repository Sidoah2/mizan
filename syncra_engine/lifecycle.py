"""
SYNCRA State Machine & Snapshot Immutability Engine
Enforces the 3-state lifecycle: SAISIE -> EN_CALCUL -> CLOTURE
Prevents in-place mutation of closed snapshots (criminal-grade immutability).
"""

from enum import Enum
from typing import Dict, Any, Optional
import uuid
import datetime
from .diagnostic_errors import SyncraSecurityException, SyncraException
from .idempotency import SyncraIdempotencyService


class CycleState(str, Enum):
    SAISIE = "SAISIE"
    EN_CALCUL = "EN_CALCUL"
    CLOTURE = "CLOTURE"


class Manifest:
    """Represents frozen cycle inputs."""
    def __init__(self, cycle_id: str, dossier_id: str, inputs: Dict[str, Any]):
        self.manifest_id = str(uuid.uuid4())
        self.cycle_id = cycle_id
        self.dossier_id = dossier_id
        self.inputs = inputs
        self.manifest_hash = SyncraIdempotencyService.generate_manifest_hash(inputs)
        self.created_at = datetime.datetime.now(datetime.timezone.utc)


class Snapshot:
    """Represents frozen cycle calculation results."""
    def __init__(
        self,
        cycle_id: str,
        dossier_id: str,
        manifest_id: str,
        results: Dict[str, Any],
        state: CycleState = CycleState.EN_CALCUL
    ):
        self.snapshot_id = str(uuid.uuid4())
        self.cycle_id = cycle_id
        self.dossier_id = dossier_id
        self.manifest_id = manifest_id
        self._results = results
        self.snapshot_hash = SyncraIdempotencyService.generate_snapshot_hash(results)
        self.state = state
        self.created_at = datetime.datetime.now(datetime.timezone.utc)
        self.closed_at: Optional[datetime.datetime] = None

    @property
    def results(self) -> Dict[str, Any]:
        return self._results

    def update_results(self, new_results: Dict[str, Any]):
        """
        Attempts to update snapshot results.
        If state == CLOTURE, this MUST raise SyncraSecurityException.
        """
        if self.state == CycleState.CLOTURE:
            raise SyncraSecurityException(
                code="SYNCRA_SECURITY_VIOLATION",
                message="Snapshot clôturé: mutation interdite.",
                details={"snapshot_id": self.snapshot_id, "state": self.state.value}
            )
        self._results = new_results
        self.snapshot_hash = SyncraIdempotencyService.generate_snapshot_hash(new_results)

    def seal_final(self):
        """Transitions snapshot to final immutable state CLOTURE."""
        self.state = CycleState.CLOTURE
        self.closed_at = datetime.datetime.now(datetime.timezone.utc)


class PayrollCycle:
    """Manages the lifecycle of a payroll cycle."""
    def __init__(self, cycle_id: str, dossier_id: str, employee_id: str, period_start: str, period_end: str):
        self.cycle_id = cycle_id
        self.dossier_id = dossier_id
        self.employee_id = employee_id
        self.period_start = period_start
        self.period_end = period_end
        self.state = CycleState.SAISIE
        self.current_manifest: Optional[Manifest] = None
        self.current_snapshot: Optional[Snapshot] = None
        self.attempt_count = 0

    def freeze_for_calculation(self, inputs: Dict[str, Any]) -> Manifest:
        """Transitions from SAISIE to EN_CALCUL by freezing inputs in a Manifest."""
        if self.state != CycleState.SAISIE:
            raise SyncraException(
                code="SYNCRA_INVALID_LIFECYCLE_TRANSITION",
                message=f"Cannot freeze for calculation from state {self.state.value}. Must be in SAISIE."
            )
        self.state = CycleState.EN_CALCUL
        self.attempt_count += 1
        self.current_manifest = Manifest(self.cycle_id, self.dossier_id, inputs)
        return self.current_manifest

    def rollback_to_saisie(self) -> None:
        """
        Rollback from EN_CALCUL to SAISIE to allow user corrections.
        Does NOT overwrite previous attempt history.
        """
        if self.state == CycleState.CLOTURE:
            raise SyncraSecurityException(
                code="SYNCRA_SECURITY_VIOLATION",
                message="Cycle is closed (CLOTURE): mutation or rollback strictly forbidden."
            )
        if self.state != CycleState.EN_CALCUL:
            raise SyncraException(
                code="SYNCRA_INVALID_LIFECYCLE_TRANSITION",
                message=f"Cannot rollback to SAISIE from state {self.state.value}. Only EN_CALCUL can be rolled back."
            )
        self.state = CycleState.SAISIE
        # Note: Previous manifest/snapshots remain archived in history

    def close_cycle(self, snapshot: Snapshot) -> None:
        """
        Transitions from EN_CALCUL to CLOTURE.
        Requires a valid sealed Snapshot.
        """
        if self.state != CycleState.EN_CALCUL:
            raise SyncraException(
                code="SYNCRA_INVALID_LIFECYCLE_TRANSITION",
                message=f"Cannot close cycle from state {self.state.value}. Must be in EN_CALCUL."
            )
        if snapshot.cycle_id != self.cycle_id:
            raise SyncraSecurityException(
                code="SYNCRA_CYCLE_MISMATCH",
                message="Snapshot does not belong to this cycle."
            )
        snapshot.seal_final()
        self.current_snapshot = snapshot
        self.state = CycleState.CLOTURE


# Aliases for consistent naming
PayrollCycleState = CycleState
SyncraManifest = Manifest
SyncraSnapshot = Snapshot


class SyncraLifecycleManager:
    """High-level manager for payroll cycles, manifests, and snapshots."""
    def __init__(self):
        self.cycles: Dict[str, PayrollCycle] = {}

    def _cycle_key(self, dossier_id: str, period: str) -> str:
        return f"{dossier_id}::{period}"

    def create_cycle(self, dossier_id: str, period: str, employee_id: str = "SYNTH-EMP-001") -> PayrollCycle:
        key = self._cycle_key(dossier_id, period)
        cycle_id = f"CYC-{uuid.uuid4().hex[:8]}"
        cycle = PayrollCycle(
            cycle_id=cycle_id,
            dossier_id=dossier_id,
            employee_id=employee_id,
            period_start=f"{period}-01",
            period_end=f"{period}-30"
        )
        self.cycles[key] = cycle
        return cycle

    def get_cycle(self, dossier_id: str, period: str) -> PayrollCycle:
        key = self._cycle_key(dossier_id, period)
        if key not in self.cycles:
            raise SyncraException(code="SYNCRA_CYCLE_NOT_FOUND", message=f"No cycle found for {key}")
        return self.cycles[key]

    def transition_to_en_calcul(self, dossier_id: str, period: str, inputs: Dict[str, Any]) -> Manifest:
        cycle = self.get_cycle(dossier_id, period)
        return cycle.freeze_for_calculation(inputs)

    def revert_to_saisie_for_correction(self, dossier_id: str, period: str, reason: str = "") -> None:
        cycle = self.get_cycle(dossier_id, period)
        cycle.rollback_to_saisie()

    def close_and_freeze_cycle(
        self,
        dossier_id: str,
        period: str,
        calculation_results: Dict[str, Any],
        closed_by: str = "system"
    ) -> Snapshot:
        cycle = self.get_cycle(dossier_id, period)
        manifest_id = cycle.current_manifest.manifest_id if cycle.current_manifest else str(uuid.uuid4())
        snapshot = Snapshot(
            cycle_id=cycle.cycle_id,
            dossier_id=dossier_id,
            manifest_id=manifest_id,
            results=calculation_results,
            state=CycleState.EN_CALCUL
        )
        cycle.close_cycle(snapshot)
        return snapshot
