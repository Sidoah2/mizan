"""
SYNCRA Bitemporal Value Manager
Implements bitemporal data management:
1. Valid Time (Business/legal effect): valid_from -> valid_to
2. Transaction Time (System audit recording): tx_from -> tx_to
Strictly avoids in-place overwriting; historical corrections close the previous
transaction window and open a new active slice.
"""

from datetime import date, datetime, timezone
from typing import Dict, Any, List, Optional
import uuid
from .diagnostic_errors import SyncraException


class BitemporalRecord:
    def __init__(
        self,
        scope_type: str,
        scope_id: str,
        field_code: str,
        value: Any,
        valid_from: date,
        valid_to: Optional[date] = None,
        tx_from: Optional[datetime] = None,
        tx_to: Optional[datetime] = None,
        source_ref: Optional[str] = None,
        created_by: Optional[str] = None
    ):
        self.value_id = str(uuid.uuid4())
        self.scope_type = scope_type
        self.scope_id = scope_id
        self.field_code = field_code
        self.value = value
        self.valid_from = valid_from
        self.valid_to = valid_to
        self.tx_from = tx_from or datetime.now(timezone.utc)
        self.tx_to = tx_to
        self.source_ref = source_ref
        self.created_by = created_by

    def is_active_tx(self, as_of_tx: datetime) -> bool:
        """Checks if record was known in the system at transaction time as_of_tx."""
        if self.tx_from > as_of_tx:
            return False
        if self.tx_to is not None and self.tx_to <= as_of_tx:
            return False
        return True

    def is_valid_at(self, as_of_date: date) -> bool:
        """Checks if value is legally applicable at business date as_of_date."""
        if self.valid_from > as_of_date:
            return False
        if self.valid_to is not None and self.valid_to < as_of_date:
            return False
        return True


class BitemporalStore:
    def __init__(self, dossier_id: str):
        self.dossier_id = dossier_id
        self._records: List[BitemporalRecord] = []

    def set_value(
        self,
        scope_type: str,
        scope_id: str,
        field_code: str,
        value: Any,
        valid_from: date,
        valid_to: Optional[date] = None,
        source_ref: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> BitemporalRecord:
        """
        Inserts or corrects a value without destructive overwriting.
        Closes current active transaction window and inserts new record.
        """
        now = datetime.now(timezone.utc)

        # Close overlapping active records in transaction time
        for rec in self._records:
            if (
                rec.scope_type == scope_type
                and rec.scope_id == scope_id
                and rec.field_code == field_code
                and rec.tx_to is None
                and rec.valid_from == valid_from
            ):
                rec.tx_to = now

        new_record = BitemporalRecord(
            scope_type=scope_type,
            scope_id=scope_id,
            field_code=field_code,
            value=value,
            valid_from=valid_from,
            valid_to=valid_to,
            tx_from=now,
            tx_to=None,
            source_ref=source_ref,
            created_by=created_by
        )
        self._records.append(new_record)
        return new_record

    def get_value(
        self,
        scope_type: str,
        scope_id: str,
        field_code: str,
        as_of_valid_date: date,
        as_of_tx_time: Optional[datetime] = None
    ) -> Optional[Any]:
        """
        Retrieves the exact effective value as legally valid at `as_of_valid_date`
        and as recorded in the system at `as_of_tx_time`.
        """
        tx_target = as_of_tx_time or datetime.now(timezone.utc)

        matching = [
            rec for rec in self._records
            if rec.scope_type == scope_type
            and rec.scope_id == scope_id
            and rec.field_code == field_code
            and rec.is_active_tx(tx_target)
            and rec.is_valid_at(as_of_valid_date)
        ]

        if not matching:
            return None

        # Return the most specific matching slice (highest valid_from)
        matching.sort(key=lambda r: r.valid_from, reverse=True)
        return matching[0].value

    def get_history(self, scope_id: str, field_code: str) -> List[Dict[str, Any]]:
        """Returns the complete immutable historical audit trail of a field."""
        return [
            {
                "value_id": rec.value_id,
                "value": rec.value,
                "valid_from": rec.valid_from.isoformat(),
                "valid_to": rec.valid_to.isoformat() if rec.valid_to else None,
                "tx_from": rec.tx_from.isoformat(),
                "tx_to": rec.tx_to.isoformat() if rec.tx_to else None,
                "is_current": rec.tx_to is None
            }
            for rec in self._records
            if rec.scope_id == scope_id and rec.field_code == field_code
        ]
