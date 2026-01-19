"""
Neighbor counting and density computation.

Calculates neighbor counts within a radius and computes site density.
"""

import pandas as pd
import numpy as np
from backend.spatial_index import build_ball_tree, coords_to_radians, km_to_radians


def calculate_density(
    df: pd.DataFrame,
    radius_km: float = 2.0
) -> pd.Series:
    """
    Calculate site density using spatial indexing.
    
    Density = (number of neighbors within radius) / (π * radius²)
    Excludes self from neighbor count.
    
    Args:
        df: DataFrame with 'lat' and 'lon' columns
        radius_km: Search radius in kilometers (default 2.0)
        
    Returns:
        Series with density values (sites per km²)
    """
    if len(df) == 0:
        return pd.Series(dtype=float)
    
    # Convert lat/lon to radians for BallTree
    coords_rad = coords_to_radians(df)
    
    # Create BallTree with Haversine metric
    tree = build_ball_tree(coords_rad)
    
    # Query all points within radius (in radians)
    radius_rad = km_to_radians(radius_km)
    neighbor_counts = tree.query_radius(coords_rad, r=radius_rad, count_only=True)
    
    # Exclude self from count
    neighbor_counts = neighbor_counts - 1
    
    # Calculate density: neighbors / (π * radius²)
    area_km2 = np.pi * (radius_km ** 2)
    density = neighbor_counts / area_km2
    
    return pd.Series(density, index=df.index, name='density')
