"""
Phase 1: Data Extraction & Dimensionality Reduction
Parses GCTX and GZ metadata files, performs filtering and data transformation.
"""

import pandas as pd
import numpy as np
import gzip
import logging
import config
from logger import setup_logger, log_filtering_stats, log_data_shape


logger = setup_logger(__name__)


def parse_gctx_file(filepath, chunk_size=10000):
    """
    Parse GCTX file in chunks for memory efficiency.
    GCTX format contains a header line followed by tab-separated data.
    
    Args:
        filepath (str): Path to GCTX file.
        chunk_size (int): Number of rows to read at once.
    
    Returns:
        pd.DataFrame: Parsed genetic signatures data.
    
    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If file format is invalid.
    """
    logger.info(f"Parsing GCTX file: {filepath}")
    
    try:
        # Read GCTX file (typically tab-separated with header)
        # GCTX is a binary format, but for this pipeline we handle the text version
        data = pd.read_csv(
            filepath,
            sep='\t',
            dtype_backend='numpy_nullable',
            low_memory=False
        )
        log_data_shape(data, "Raw GCTX data loaded")
        return data
    
    except FileNotFoundError:
        logger.error(f"GCTX file not found: {filepath}")
        raise
    except Exception as e:
        logger.error(f"Error parsing GCTX file: {e}")
        raise ValueError(f"Invalid GCTX file format: {e}")


def parse_metadata_file(filepath, compression='gzip'):
    """
    Parse metadata files (gene, signature, or perturbagen info).
    
    Args:
        filepath (str): Path to metadata file.
        compression (str): Compression type ('gzip' or None).
    
    Returns:
        pd.DataFrame: Parsed metadata.
    
    Raises:
        FileNotFoundError: If file does not exist.
    """
    logger.info(f"Parsing metadata file: {filepath}")
    
    try:
        if compression == 'gzip':
            with gzip.open(filepath, 'rt') as f:
                data = pd.read_csv(f, sep='\t', low_memory=False)
        else:
            data = pd.read_csv(filepath, sep='\t', low_memory=False)
        
        log_data_shape(data, f"Metadata loaded from {filepath}")
        return data
    
    except FileNotFoundError:
        logger.error(f"Metadata file not found: {filepath}")
        raise
    except Exception as e:
        logger.error(f"Error parsing metadata file: {e}")
        raise


def filter_by_z_score(data, z_score_col='z_score', threshold=None):
    """
    Filter genetic signatures by Z-score to remove biological noise.
    Keeps significant hits (|Z| >= threshold).
    
    Args:
        data (pd.DataFrame): Input data with Z-score column.
        z_score_col (str): Name of Z-score column.
        threshold (float): Z-score threshold. Defaults to config.Z_SCORE_THRESHOLD.
    
    Returns:
        pd.DataFrame: Filtered data.
    """
    if threshold is None:
        threshold = config.Z_SCORE_THRESHOLD
    
    original_count = len(data)
    
    # Filter for absolute Z-score >= threshold
    filtered_data = data[np.abs(data[z_score_col]) >= threshold].copy()
    
    log_filtering_stats(original_count, len(filtered_data), 
                       f"Z-score filtering (|Z| >= {threshold})")
    
    return filtered_data


def validate_data_quality(data, description="Data"):
    """
    Validate data quality and report issues.
    
    Args:
        data (pd.DataFrame): Data to validate.
        description (str): Description for logging.
    
    Returns:
        dict: Validation report with statistics.
    """
    report = {
        'shape': data.shape,
        'null_counts': data.isnull().sum(),
        'null_percentage': (data.isnull().sum() / len(data) * 100).round(2),
        'duplicates': data.duplicated().sum(),
        'memory_mb': data.memory_usage(deep=True).sum() / 1024**2
    }
    
    logger.info(f"\n{description} Quality Report:")
    logger.info(f"  Shape: {report['shape']}")
    logger.info(f"  Null values: {report['null_counts'].sum()}")
    logger.info(f"  Duplicates: {report['duplicates']}")
    logger.info(f"  Memory: {report['memory_mb']:.2f} MB")
    
    # Check for concerning null percentages
    high_null_cols = report['null_percentage'][report['null_percentage'] > 50]
    if len(high_null_cols) > 0:
        logger.warning(f"Columns with >50% null values: {high_null_cols.to_dict()}")
    
    return report


def melt_wide_to_long(data, id_vars, var_name='gene', value_name='z_score'):
    """
    Transform wide data (genes as columns) to long format (one row per gene per compound).
    
    Args:
        data (pd.DataFrame): Wide format data.
        id_vars (list): Columns to keep as identifiers.
        var_name (str): Name for the new variable column.
        value_name (str): Name for the new value column.
    
    Returns:
        pd.DataFrame: Long format data.
    """
    logger.info(f"Melting data from wide to long format...")
    original_shape = data.shape
    
    melted = pd.melt(data, id_vars=id_vars, var_name=var_name, value_name=value_name)
    
    logger.info(f"Shape transformed: {original_shape} -> {melted.shape}")
    log_data_shape(melted, "Melted data")
    
    return melted


def remove_duplicates(data, subset=None, keep='first'):
    """
    Remove duplicate rows based on specified columns.
    
    Args:
        data (pd.DataFrame): Input data.
        subset (list): Columns to consider for duplicates.
        keep (str): Which duplicates to keep ('first', 'last', False).
    
    Returns:
        pd.DataFrame: Data with duplicates removed.
    """
    original_count = len(data)
    deduplicated = data.drop_duplicates(subset=subset, keep=keep)
    
    log_filtering_stats(original_count, len(deduplicated), "Duplicate removal")
    
    return deduplicated


def create_compound_metadata(pert_info_data, gene_data):
    """
    Create compound metadata table from perturbagen info.
    
    Args:
        pert_info_data (pd.DataFrame): Perturbagen information.
        gene_data (pd.DataFrame): Gene information (optional for enrichment).
    
    Returns:
        pd.DataFrame: Compound metadata with key fields.
    """
    logger.info("Creating compound metadata table...")
    
    # Select relevant columns (customize based on actual file structure)
    relevant_cols = [col for col in ['pert_iname', 'moa', 'target', 'canonical_smiles', 'pubchem_cid'] 
                     if col in pert_info_data.columns]
    
    metadata = pert_info_data[relevant_cols].drop_duplicates(subset=['pert_iname'])
    
    logger.info(f"Created metadata for {len(metadata)} unique compounds")
    log_data_shape(metadata, "Compound metadata")
    
    return metadata


def save_processed_data(compound_data, signature_data, 
                       compound_path=None, signature_path=None):
    """
    Save processed data to CSV files.
    
    Args:
        compound_data (pd.DataFrame): Compound metadata.
        signature_data (pd.DataFrame): Genetic signatures.
        compound_path (str): Path for compound CSV. Defaults to config value.
        signature_path (str): Path for signature CSV. Defaults to config value.
    """
    if compound_path is None:
        compound_path = config.COMPOUND_METADATA_CSV
    if signature_path is None:
        signature_path = config.GENETIC_SIGNATURES_CSV
    
    logger.info(f"Saving compound metadata to {compound_path}")
    compound_data.to_csv(compound_path, index=False)
    logger.info(f"✓ Saved {len(compound_data)} compound records")
    
    logger.info(f"Saving genetic signatures to {signature_path}")
    signature_data.to_csv(signature_path, index=False)
    logger.info(f"✓ Saved {len(signature_data)} signature records")
