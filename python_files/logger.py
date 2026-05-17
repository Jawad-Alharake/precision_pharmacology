"""
Logging utility for the Precision Pharmacology pipeline.
Provides structured logging for debugging and monitoring pipeline execution.
"""

import logging
import sys
from datetime import datetime
import config


def setup_logger(name=None, log_file=None):
    """
    Set up a logger with both file and console handlers.
    
    Args:
        name (str): Logger name. Defaults to root logger if None.
        log_file (str): Path to log file. Defaults to config.LOG_FILE if None.
    
    Returns:
        logging.Logger: Configured logger instance.
    """
    if log_file is None:
        log_file = config.LOG_FILE
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, config.LOG_LEVEL))
    
    # Avoid duplicate handlers
    if logger.hasHandlers():
        return logger
    
    # File handler
    file_handler = logging.FileHandler(log_file, mode='a')
    file_handler.setLevel(getattr(logging, config.LOG_LEVEL))
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, config.LOG_LEVEL))
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def log_phase_start(phase_number, phase_name):
    """Log the start of a pipeline phase."""
    logger = logging.getLogger(__name__)
    logger.info(f"\n{'='*80}")
    logger.info(f"PHASE {phase_number}: {phase_name}")
    logger.info(f"Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"{'='*80}")


def log_phase_end(phase_number, phase_name, summary):
    """Log the end of a pipeline phase with summary statistics."""
    logger = logging.getLogger(__name__)
    logger.info(f"\nPHASE {phase_number} COMPLETE: {phase_name}")
    logger.info(f"Summary: {summary}")
    logger.info(f"Completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")


def log_data_shape(data, description):
    """Log the shape and basic stats of a dataframe."""
    logger = logging.getLogger(__name__)
    logger.info(f"{description} - Shape: {data.shape}, Memory: {data.memory_usage(deep=True).sum() / 1024**2:.2f} MB")


def log_filtering_stats(original_count, filtered_count, filter_description):
    """Log filtering statistics."""
    logger = logging.getLogger(__name__)
    removed = original_count - filtered_count
    percentage = (removed / original_count * 100) if original_count > 0 else 0
    logger.info(f"{filter_description}: Removed {removed} rows ({percentage:.2f}%) - Remaining: {filtered_count}")
