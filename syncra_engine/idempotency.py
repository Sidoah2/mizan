"""
SYNCRA Idempotency Engine
Computes deterministic request keys (request_key_sha256) and snapshot hashes.
Ensures 100% bitwise parity and idempotency across all engine runs.
"""

import hashlib
import json
from decimal import Decimal
from typing import Any, Dict


class DecimalEncoder(json.JSONEncoder):
    """Ensures deterministic decimal encoding without float IEEE 754 precision drifts."""
    def default(self, obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return str(obj.quantize(Decimal("0.01")))
        return super().default(obj)


class SyncraIdempotencyService:
    @staticmethod
    def canonical_json(data: Dict[str, Any]) -> str:
        """
        Produces a canonical, strictly sorted, whitespace-trimmed JSON string.
        Keys are sorted recursively, preventing hashing mismatches.
        """
        return json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            cls=DecimalEncoder,
            ensure_ascii=False
        )

    @classmethod
    def compute_hash(cls, data: Any) -> str:
        """Computes SHA-256 hash from string or canonical dictionary."""
        if isinstance(data, dict):
            raw_str = cls.canonical_json(data)
        elif isinstance(data, bytes):
            return hashlib.sha256(data).hexdigest()
        else:
            raw_str = str(data)
        
        return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()

    @classmethod
    def generate_manifest_hash(cls, inputs_payload: Dict[str, Any]) -> str:
        """Calculates SHA-256 manifest hash from canonical inputs."""
        return cls.compute_hash(inputs_payload)

    @classmethod
    def generate_snapshot_hash(cls, results_payload: Dict[str, Any]) -> str:
        """Calculates SHA-256 snapshot hash from canonical results."""
        return cls.compute_hash(results_payload)

    @classmethod
    def compute_render_idempotency_key(
        cls,
        dossier_id: str,
        snapshot_id: str,
        document_type: str,
        lang: str,
        template_id: str,
        template_version: str,
        policy_id: str,
        engine_version: str,
        font_manifest_hash: str
    ) -> str:
        """
        Calculates the unique request_key_sha256 for document rendering.
        Guarantees that requesting the same render with identical parameters
        always maps to the exact same hash and binary artifact.
        """
        components = [
            f"dossier_id={dossier_id}",
            f"snapshot_id={snapshot_id}",
            f"document_type={document_type}",
            f"lang={lang}",
            f"template_id={template_id}",
            f"template_version={template_version}",
            f"policy_id={policy_id}",
            f"engine_version={engine_version}",
            f"font_manifest_hash={font_manifest_hash}",
        ]
        # Sort components for deterministic canonical order
        components.sort()
        canonical_request_str = "&".join(components)
        return hashlib.sha256(canonical_request_str.encode("utf-8")).hexdigest()


class SyncraCanonicalSerializer:
    """Serializes objects to deterministic canonical UTF-8 bytes."""
    @staticmethod
    def serialize(data: Any) -> bytes:
        raw_str = SyncraIdempotencyService.canonical_json(data)
        return raw_str.encode("utf-8")
