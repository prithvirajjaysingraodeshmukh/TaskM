"""
Spatial indexing and coordinate conversion utilities.

Handles BallTree construction with Haversine metric and coordinate transformations.
"""

import numpy as np
from sklearn.neighbors import BallTree

# Earth's radius in kilometers for Haversine distance
EARTH_RADIUS_KM = 6371.0


def haversine_distance(
    lat1: np.ndarray, lon1: np.ndarray,
    lat2: np.ndarray, lon2: np.ndarray
) -> np.ndarray:
    """
    Calculate Haversine distance between two sets of coordinates.
    
    Args:
        lat1, lon1: First set of coordinates (can be arrays)
        lat2, lon2: Second set of coordinates (can be arrays)
        
    Returns:
        Distance in kilometers
    """
    # Convert to radians
    lat1_rad = np.radians(lat1)
    lon1_rad = np.radians(lon1)
    lat2_rad = np.radians(lat2)
    lon2_rad = np.radians(lon2)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = (
        np.sin(dlat / 2) ** 2 +
        np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2) ** 2
    )
    c = 2 * np.arcsin(np.sqrt(a))
    distance = EARTH_RADIUS_KM * c
    
    return distance


def build_ball_tree(coords_rad: np.ndarray) -> BallTree:
    """
    Build BallTree spatial index with Haversine metric.
    
    Args:
        coords_rad: Coordinates in radians, shape (n_points, 2) with [lat, lon]
        
    Returns:
        BallTree instance configured for Haversine distance
    """
    return BallTree(coords_rad, metric='haversine')


def coords_to_radians(df) -> np.ndarray:
    """
    Convert latitude/longitude DataFrame columns to radians.
    
    Args:
        df: DataFrame with 'lat' and 'lon' columns
        
    Returns:
        Array of shape (n_points, 2) with coordinates in radians
    """
    return np.radians(df[['lat', 'lon']].values)


def km_to_radians(km: float) -> float:
    """
    Convert distance in kilometers to radians for BallTree queries.
    
    Args:
        km: Distance in kilometers
        
    Returns:
        Distance in radians
    """
    return km / EARTH_RADIUS_KM
