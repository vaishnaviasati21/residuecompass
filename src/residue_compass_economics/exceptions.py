"""
Custom domain exceptions for Residue Compass Part 4.
"""

class ResidueCompassError(Exception):
    """Base exception for all Residue Compass errors."""
    pass


class ValidationError(ResidueCompassError):
    """Raised when data contracts, schemas, units, or constraints fail validation."""
    def __init__(self, message: str, field: str | None = None, details: dict | None = None):
        super().__init__(message)
        self.field = field
        self.details = details or {}


class CalculationError(ResidueCompassError):
    """Raised when numerical errors, division by zero, or invalid economics occur."""
    pass


class InfeasibleMatchError(ResidueCompassError):
    """Raised when matching constraints cannot be satisfied."""
    def __init__(self, message: str, village_id: str | None = None, reason: str | None = None):
        super().__init__(message)
        self.village_id = village_id
        self.reason = reason
