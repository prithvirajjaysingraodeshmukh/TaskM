"""
Co-location grouping logic using graph-based connected components.

Groups sites that are within a distance threshold using Union-Find algorithm.
"""

from typing import Tuple
import pandas as pd
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components
from backend.spatial_index import build_ball_tree, coords_to_radians, km_to_radians


def find_co_location_groups(
    df: pd.DataFrame,
    threshold_m: float = 100.0
) -> Tuple[pd.Series, pd.Series]:
    """
    Find co-location groups using graph-based connected components.
    
    Two sites are in the same group if their distance < threshold.
    Uses connected components algorithm on a graph where edges exist
    when distance < threshold.
    
    Args:
        df: DataFrame with 'lat' and 'lon' columns
        threshold_m: Distance threshold in meters (default 100.0)
        
    Returns:
        Tuple of (group_id Series, group_size Series)
    """
    if len(df) == 0:
        return pd.Series(dtype=str), pd.Series(dtype=int)
    
    threshold_km = threshold_m / 1000.0
    
    # Convert lat/lon to radians for BallTree
    coords_rad = coords_to_radians(df)
    
    # Create BallTree
    tree = build_ball_tree(coords_rad)
    
    # Query all points within threshold
    threshold_rad = km_to_radians(threshold_km)
    neighbors = tree.query_radius(coords_rad, r=threshold_rad)
    
    # Build sparse adjacency matrix for efficient connected components
    n = len(df)
    row_indices = []
    col_indices = []
    
    for i, neighbor_indices in enumerate(neighbors):
        for j in neighbor_indices:
            if i != j:  # Exclude self
                row_indices.append(i)
                col_indices.append(j)
    
    # Create sparse CSR matrix (symmetric, undirected graph)
    if len(row_indices) > 0:
        # Add symmetric edges (undirected graph) - use 1.0 for edge weights
        all_rows = row_indices + col_indices
        all_cols = col_indices + row_indices
        adjacency = csr_matrix((np.ones(len(all_rows), dtype=np.float64), (all_rows, all_cols)), shape=(n, n))
    else:
        # No edges, each node is its own component
        adjacency = csr_matrix((n, n), dtype=np.float64)
    
    # Find connected components using scipy (fast and non-recursive)
    n_components, labels = connected_components(csgraph=adjacency, directed=False, return_labels=True)
    
    # Group nodes by component label
    components = {}
    for i, label in enumerate(labels):
        if label not in components:
            components[label] = []
        components[label].append(i)
    
    # Create group_id as deterministic hash of sorted member site_ids
    group_ids = {}
    for label, component_indices in components.items():
        # Get site_ids for this component
        component_site_ids = sorted([df.iloc[i]['site_id'] for i in component_indices])
        # Create deterministic hash (using hash of sorted tuple)
        group_id = str(hash(tuple(component_site_ids)))
        for i in component_indices:
            group_ids[i] = group_id
    
    # Create Series with group_id and group_size
    group_id_series = pd.Series(
        [group_ids.get(i, '') for i in range(len(df))],
        index=df.index,
        name='group_id'
    )
    
    # Calculate group sizes
    group_sizes = group_id_series.value_counts()
    group_size_series = group_id_series.map(group_sizes).rename('group_size')
    
    return group_id_series, group_size_series
