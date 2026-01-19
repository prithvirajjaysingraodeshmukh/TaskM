"""
Processing pipeline orchestration.

Coordinates the full site analysis workflow: validation → density → co-location → classification.
"""

from typing import Dict, List, Optional, Tuple
import pandas as pd
from backend.validator import validate_csv
from backend.neighbors import calculate_density
from backend.colocation import find_co_location_groups
from backend.classifier import classify_sites


def process_sites(
    df: pd.DataFrame,
    radius_km: float = 2.0,
    co_location_threshold_m: float = 100.0,
    classification_mode: str = 'quantile',
    classification_thresholds: Optional[Dict[str, float]] = None
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Complete processing pipeline for site analysis.
    
    Args:
        df: Input DataFrame
        radius_km: Radius for density calculation (km)
        co_location_threshold_m: Threshold for co-location grouping (meters)
        classification_mode: 'quantile' or 'threshold'
        classification_thresholds: Optional thresholds for threshold mode
        
    Returns:
        Tuple of (enriched DataFrame, list of processing messages)
    """
    messages = []
    
    # Step 1: Validate
    df_clean, validation_errors = validate_csv(df)
    messages.extend(validation_errors)
    
    if len(df_clean) == 0:
        messages.append("No valid rows after validation")
        return df_clean, messages
    
    # Step 2: Calculate density
    density = calculate_density(df_clean, radius_km=radius_km)
    df_clean = df_clean.copy()
    df_clean['density'] = density
    
    # Step 3: Find co-location groups
    group_id, group_size = find_co_location_groups(
        df_clean, threshold_m=co_location_threshold_m
    )
    df_clean['group_id'] = group_id
    df_clean['group_size'] = group_size
    
    # Step 4: Classify
    area_class = classify_sites(
        df_clean,
        mode=classification_mode,
        thresholds=classification_thresholds
    )
    df_clean['area_class'] = area_class
    
    messages.append(f"Processed {len(df_clean)} sites successfully")
    
    return df_clean, messages
