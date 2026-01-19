"""
Area classification logic.

Classifies sites into Rural, Suburban, Urban, Dense categories
using either quantile-based or threshold-based methods.
"""

from typing import Dict, Optional
import pandas as pd


def classify_sites(
    df: pd.DataFrame,
    mode: str = 'quantile',
    thresholds: Optional[Dict[str, float]] = None
) -> pd.Series:
    """
    Classify sites into Rural, Suburban, Urban, Dense based on density.
    
    Args:
        df: DataFrame with 'density' and 'cluster_id' columns
        mode: 'quantile' or 'threshold'
        thresholds: Optional dict with 'rural', 'suburban', 'urban' keys
                    (only used in threshold mode)
        
    Returns:
        Series with area_class values
    """
    if 'density' not in df.columns:
        raise ValueError("DataFrame must have 'density' column")
    
    if mode == 'quantile':
        return _classify_quantile(df)
    elif mode == 'threshold':
        return _classify_threshold(df, thresholds)
    else:
        raise ValueError(f"Invalid mode: {mode}. Must be 'quantile' or 'threshold'")


def _classify_quantile(df: pd.DataFrame) -> pd.Series:
    """
    Classify using quantile-based method per cluster.
    
    Calculates Q25, Q50, Q75 for each cluster_id and assigns classes accordingly.
    """
    area_classes = pd.Series(index=df.index, dtype=str)
    
    for cluster_id in df['cluster_id'].unique():
        cluster_mask = df['cluster_id'] == cluster_id
        cluster_densities = df.loc[cluster_mask, 'density']
        
        if len(cluster_densities) == 0:
            continue
        
        # Calculate percentiles
        q25 = cluster_densities.quantile(0.25)
        q50 = cluster_densities.quantile(0.50)
        q75 = cluster_densities.quantile(0.75)
        
        # Classify based on percentiles
        cluster_classes = pd.Series(index=cluster_densities.index, dtype=str)
        cluster_classes[cluster_densities <= q25] = 'Rural'
        cluster_classes[(cluster_densities > q25) & (cluster_densities <= q50)] = 'Suburban'
        cluster_classes[(cluster_densities > q50) & (cluster_densities <= q75)] = 'Urban'
        cluster_classes[cluster_densities > q75] = 'Dense'
        
        area_classes.loc[cluster_mask] = cluster_classes
    
    return area_classes.rename('area_class')


def _classify_threshold(df: pd.DataFrame, thresholds: Optional[Dict[str, float]] = None) -> pd.Series:
    """
    Classify using fixed threshold values.
    
    Args:
        df: DataFrame with 'density' column
        thresholds: Dict with 'rural', 'suburban', 'urban' keys
    """
    if thresholds is None:
        # Default thresholds (sites per km²)
        thresholds = {
            'rural': 10.0,
            'suburban': 50.0,
            'urban': 200.0
        }
    
    area_classes = pd.Series(index=df.index, dtype=str)
    density = df['density']
    
    area_classes[density <= thresholds['rural']] = 'Rural'
    area_classes[
        (density > thresholds['rural']) & (density <= thresholds['suburban'])
    ] = 'Suburban'
    area_classes[
        (density > thresholds['suburban']) & (density <= thresholds['urban'])
    ] = 'Urban'
    area_classes[density > thresholds['urban']] = 'Dense'
    
    return area_classes.rename('area_class')
