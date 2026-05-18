"""
Precision Pharmacology Pipeline Package
An end-to-end data engineering pipeline for drug repurposing.

Phases:
1. Data Extraction & Dimensionality Reduction
2. Relational Database Architecture
3. Business Analytics & Insight Generation
4. Literature Footprint & Risk Assessment
5. Temporal Pharmacodynamics & Clinical Profile Classification

Usage:
    from python_files.pipeline_orchestrator import PipelineOrchestrator
    
    orchestrator = PipelineOrchestrator()
    report = orchestrator.run_full_pipeline(gctx_path, metadata_paths)
"""

from .exceptions import (
    PrecisionPharmacologyError,
    DataExtractionError,
    DataValidationError,
    DatabaseError,
    AnalyticsError,
    ScraperError,
    TemporalAnalysisError,
    ConfigurationError
)

from .utils import (
    validate_dataframe,
    detect_outliers,
    normalize_z_scores,
    format_scientific_notation,
    format_percentage,
    get_data_summary,
    merge_dataframes,
    safe_cast_column,
    get_column_statistics,
    batch_process
)

from .pipeline_orchestrator import PipelineOrchestrator

__version__ = "1.0.0"
__author__ = "Jawad Alharake"
__all__ = [
    # Exceptions
    'PrecisionPharmacologyError',
    'DataExtractionError',
    'DataValidationError',
    'DatabaseError',
    'AnalyticsError',
    'ScraperError',
    'TemporalAnalysisError',
    'ConfigurationError',
    # Utils
    'validate_dataframe',
    'detect_outliers',
    'normalize_z_scores',
    'format_scientific_notation',
    'format_percentage',
    'get_data_summary',
    'merge_dataframes',
    'safe_cast_column',
    'get_column_statistics',
    'batch_process',
    # Orchestrator
    'PipelineOrchestrator'
]
