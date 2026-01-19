"""
CSV and data validation logic.

Validates CSV structure, required columns, data types, and coordinate ranges.
Returns cleaned DataFrame and validation error messages.
"""

import logging
from typing import List, Tuple
import pandas as pd

logger = logging.getLogger(__name__)


def validate_csv(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """
    Validate CSV structure and drop invalid rows.
    
    Required columns: site_id, lat, lon, cluster_id
    
    Args:
        df: Input DataFrame
        
    Returns:
        Tuple of (cleaned DataFrame, list of error messages)
    """
    errors = []
    required_columns = ['site_id', 'lat', 'lon', 'cluster_id']
    
    # Check for required columns
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        errors.append(f"Missing required columns: {missing_columns}")
        return pd.DataFrame(), errors
    
    initial_count = len(df)
    
    # Drop rows with missing values in required columns
    df_clean = df[required_columns].copy()
    df_clean = df_clean.dropna(subset=required_columns)
    
    # Validate numeric types first
    for col in ['lat', 'lon']:
        non_numeric = pd.to_numeric(df_clean[col], errors='coerce').isna()
        if non_numeric.any():
            invalid_count = non_numeric.sum()
            errors.append(f"Dropped {invalid_count} rows with non-numeric {col}")
            df_clean = df_clean[~non_numeric]
    
    # Convert to proper types
    df_clean['lat'] = pd.to_numeric(df_clean['lat'])
    df_clean['lon'] = pd.to_numeric(df_clean['lon'])
    df_clean['site_id'] = df_clean['site_id'].astype(str)
    df_clean['cluster_id'] = df_clean['cluster_id'].astype(str)
    
    # Validate lat/lon ranges
    invalid_lat = (df_clean['lat'] < -90) | (df_clean['lat'] > 90)
    invalid_lon = (df_clean['lon'] < -180) | (df_clean['lon'] > 180)
    invalid_coords = invalid_lat | invalid_lon
    
    if invalid_coords.any():
        invalid_count = invalid_coords.sum()
        errors.append(f"Dropped {invalid_count} rows with invalid coordinates")
        df_clean = df_clean[~invalid_coords]
    
    # Restore other columns if they exist
    other_columns = [col for col in df.columns if col not in required_columns]
    if other_columns:
        # Reindex to match original indices
        df_other = df[other_columns].loc[df_clean.index]
        df_clean = pd.concat([df_clean, df_other], axis=1)
    
    dropped_count = initial_count - len(df_clean)
    if dropped_count > 0:
        errors.append(f"Dropped {dropped_count} invalid rows (from {initial_count} total)")
    
    if errors:
        for error in errors:
            logger.warning(error)
    
    return df_clean, errors
