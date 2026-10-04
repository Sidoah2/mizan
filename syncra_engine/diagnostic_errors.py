"""
SYNCRA Diagnostic Errors & Exceptions Hierarchy
================================================
Implements the Golden Design Rule: Never assume. Fail-Fast on missing rules,
missing translations, missing rounding policies, or regulatory conflicts.
No silent fallbacks allowed.
"""

class SyncraException(Exception):
    """Base exception for all SYNCRA engine errors."""
    def __init__(self, message: str = "", code: str = "SYNCRA_GENERIC_ERROR", details: dict = None):
        super().__init__(f"[{code}] {message}" if code else message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self):
        return {
            "error_code": self.code,
            "message": self.message,
            "details": self.details,
            "engine_status": "FAIL_FAST_ABORTED"
        }

# Aliases and specialized classes
class SyncraEngineError(SyncraException):
    """General engine execution error."""
    pass

class SyncraSecurityException(SyncraException):
    """Raised on security violations: mutating closed snapshots, cross-dossier access, etc."""
    pass

class SyncraSecurityError(SyncraSecurityException):
    """Security violation error alias."""
    pass

class SyncraGateValidationException(SyncraException):
    """Raised when one of the 4 Validation Gates fails."""
    pass

class SyncraGate1Error(SyncraGateValidationException):
    """Raised when Gate 1 (Official Algerian Gazette N1 accreditation) fails."""
    pass

class SyncraPIIError(SyncraSecurityException):
    """Raised when PII leak is detected in message queue payloads or audit traces."""
    pass

class SyncraRegulatoryConflictException(SyncraException):
    """Raised when regulatory conflicts (e.g., ANEM decision conflict or expiry) are detected."""
    pass

class SyncraMissingConfigurationException(SyncraException):
    """Raised when rounding policy, label translation, or required parameter is absent."""
    pass

class SyncraValidationError(SyncraMissingConfigurationException):
    """Validation or configuration missing error alias."""
    pass

class SyncraLifecycleError(SyncraSecurityException):
    """Lifecycle or immutable snapshot mutation violation."""
    pass

class SyncraIdempotencyError(SyncraException):
    """Idempotency or canonical serialization error."""
    pass
