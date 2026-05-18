"""
Custom exception classes for the Precision Pharmacology pipeline.
Provides structured error handling across all phases.
"""


class PrecisionPharmacologyError(Exception):
    """Base exception class for all pipeline errors."""
    pass


class DataExtractionError(PrecisionPharmacologyError):
    """Raised when data extraction or parsing fails."""
    pass


class DataValidationError(PrecisionPharmacologyError):
    """Raised when data validation fails."""
    pass


class DatabaseError(PrecisionPharmacologyError):
    """Raised when database operations fail."""
    pass


class AnalyticsError(PrecisionPharmacologyError):
    """Raised when analytics queries or processing fail."""
    pass


class ScraperError(PrecisionPharmacologyError):
    """Raised when web scraping fails."""
    pass


class TemporalAnalysisError(PrecisionPharmacologyError):
    """Raised when temporal analysis or ML classification fails."""
    pass


class ConfigurationError(PrecisionPharmacologyError):
    """Raised when configuration is invalid."""
    pass
