"""
Utility functions for the Precision Pharmacology pipeline.
Provides validation, data processing, and helper functions.
"""

from typing import Optional, Dict, List, Tuple, Union
import pandas as pd
import numpy as np
import logging
from exceptions import DataValidationError


logger = logging.getLogger(__name__)


def validate_dataframe(data: pd.DataFrame, 
                      required_columns: Optional[List[str]] = None,
                      min_rows: int = 1) -> bool:
    """
    Validate dataframe structure and content.
    
    Args:
        data (pd.DataFrame): Dataframe to validate.
        required_columns (list): List of required column names.
        min_rows (int): Minimum number of rows required.
    
    Returns:
        bool: True if valid.
        
    Raises:
        DataValidationError: If validation fails.
    """
    if data is None or not isinstance(data, pd.DataFrame):
        raise DataValidationError("Input must be a pandas DataFrame")
    
    if len(data) < min_rows:
        raise DataValidationError(f"DataFrame has {len(data)} rows, minimum {min_rows} required")
    
    if required_columns:
        missing = [col for col in required_columns if col not in data.columns]
        if missing:
            raise DataValidationError(f"Missing required columns: {missing}")
    
    return True


def detect_outliers(data: np.ndarray, method: str = 'iqr', threshold: float = 1.5) -> np.ndarray:
    """
    Detect outliers in numeric data using IQR or Z-score method.
    
    Args:
        data (np.ndarray): Input data.
        method (str): 'iqr' or 'zscore'.
        threshold (float): IQR multiplier (1.5) or Z-score threshold (3.0).
    
    Returns:
        np.ndarray: Boolean mask of outliers.
    """
    data = np.asarray(data)
    
    if method == 'iqr':
        Q1 = np.percentile(data, 25)
        Q3 = np.percentile(data, 75)
        IQR = Q3 - Q1
        lower = Q1 - threshold * IQR
        upper = Q3 + threshold * IQR
        return (data < lower) | (data > upper)
    
    elif method == 'zscore':
        z_scores = np.abs((data - np.mean(data)) / np.std(data))
        return z_scores > threshold
    
    else:
        raise ValueError(f"Unknown method: {method}")


def normalize_z_scores(data: pd.DataFrame, col: str = 'z_score', 
                       method: str = 'standard') -> pd.DataFrame:
    """
    Normalize Z-scores using specified method.
    
    Args:
        data (pd.DataFrame): Input dataframe.
        col (str): Column name to normalize.
        method (str): 'standard', 'minmax', or 'robust'.
    
    Returns:
        pd.DataFrame: Dataframe with normalized column.
    """
    data = data.copy()
    
    if col not in data.columns:
        raise DataValidationError(f"Column '{col}' not found")
    
    values = data[col].values.astype(float)
    
    if method == 'standard':
        normalized = (values - np.mean(values)) / np.std(values)
    elif method == 'minmax':
        normalized = (values - np.min(values)) / (np.max(values) - np.min(values))
    elif method == 'robust':
        Q1 = np.percentile(values, 25)
        Q3 = np.percentile(values, 75)
        normalized = (values - np.median(values)) / (Q3 - Q1)
    else:
        raise ValueError(f"Unknown normalization method: {method}")
    
    data[f'{col}_normalized'] = normalized
    return data


def format_scientific_notation(value: float, decimals: int = 2) -> str:
    """
    Format number in scientific notation.
    
    Args:
        value (float): Number to format.
        decimals (int): Decimal places.
    
    Returns:
        str: Formatted string.
    """
    return f"{value:.{decimals}e}"


def format_percentage(value: float, decimals: int = 1) -> str:
    """
    Format number as percentage.
    
    Args:
        value (float): Number to format (0-1).
        decimals (int): Decimal places.
    
    Returns:
        str: Formatted percentage string.
    """
    return f"{value * 100:.{decimals}f}%"


def get_data_summary(data: pd.DataFrame) -> Dict:
    """
    Generate comprehensive data summary statistics.
    
    Args:
        data (pd.DataFrame): Input dataframe.
    
    Returns:
        dict: Summary statistics.
    """
    summary = {
        'rows': len(data),
        'columns': len(data.columns),
        'memory_mb': data.memory_usage(deep=True).sum() / 1024**2,
        'null_count': data.isnull().sum().sum(),
        'null_percentage': (data.isnull().sum().sum() / (len(data) * len(data.columns))) * 100,
        'duplicates': data.duplicated().sum(),
        'dtypes': data.dtypes.value_counts().to_dict()
    }
    return summary


def merge_dataframes(left: pd.DataFrame, right: pd.DataFrame, 
                     on: str, how: str = 'inner') -> pd.DataFrame:
    """
    Safely merge two dataframes with validation.
    
    Args:
        left (pd.DataFrame): Left dataframe.
        right (pd.DataFrame): Right dataframe.
        on (str): Column name to merge on.
        how (str): Merge type ('inner', 'left', 'right', 'outer').
    
    Returns:
        pd.DataFrame: Merged dataframe.
        
    Raises:
        DataValidationError: If merge fails.
    """
    try:
        if on not in left.columns:
            raise DataValidationError(f"Column '{on}' not found in left dataframe")
        if on not in right.columns:
            raise DataValidationError(f"Column '{on}' not found in right dataframe")
        
        merged = pd.merge(left, right, on=on, how=how)
        logger.info(f"Merged {len(left)} + {len(right)} rows -> {len(merged)} rows ({how})")
        return merged
    
    except Exception as e:
        raise DataValidationError(f"Merge failed: {e}")


def safe_cast_column(data: pd.DataFrame, col: str, dtype: type, 
                     fill_value: Optional[Union[int, float, str]] = None) -> pd.DataFrame:
    """
    Safely cast column to specified data type.
    
    Args:
        data (pd.DataFrame): Input dataframe.
        col (str): Column to cast.
        dtype (type): Target data type.
        fill_value: Value for NaN after casting.
    
    Returns:
        pd.DataFrame: Updated dataframe.
    """
    data = data.copy()
    try:
        data[col] = data[col].astype(dtype)
        if fill_value is not None:
            data[col] = data[col].fillna(fill_value)
        return data
    except Exception as e:
        raise DataValidationError(f"Failed to cast {col} to {dtype}: {e}")


def get_column_statistics(data: pd.DataFrame, col: str) -> Dict:
    """
    Get detailed statistics for a numeric column.
    
    Args:
        data (pd.DataFrame): Input dataframe.
        col (str): Column name.
    
    Returns:
        dict: Statistics dictionary.
    """
    if col not in data.columns:
        raise DataValidationError(f"Column '{col}' not found")
    
    values = pd.to_numeric(data[col], errors='coerce').dropna()
    
    return {
        'count': len(values),
        'mean': values.mean(),
        'median': values.median(),
        'std': values.std(),
        'min': values.min(),
        'max': values.max(),
        'q1': values.quantile(0.25),
        'q3': values.quantile(0.75),
        'skewness': values.skew(),
        'kurtosis': values.kurtosis()
    }


def batch_process(data: pd.DataFrame, batch_size: int, 
                  process_func, *args, **kwargs):
    """
    Process dataframe in batches.
    
    Args:
        data (pd.DataFrame): Input dataframe.
        batch_size (int): Batch size.
        process_func: Function to apply to each batch.
        *args, **kwargs: Arguments for process_func.
    
    Yields:
        Results from process_func.
    """
    for i in range(0, len(data), batch_size):
        batch = data.iloc[i:i + batch_size]
        result = process_func(batch, *args, **kwargs)
        yield result
