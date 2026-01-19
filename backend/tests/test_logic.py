"""
Comprehensive unit tests for site analysis logic.
Includes mandatory test with 3 synthetic points in a line.
"""

import pytest
import pandas as pd
import numpy as np
from backend.validator import validate_csv
from backend.spatial_index import haversine_distance, EARTH_RADIUS_KM
from backend.neighbors import calculate_density
from backend.colocation import find_co_location_groups
from backend.classifier import classify_sites
from backend.pipeline import process_sites


class TestValidation:
    """Tests for CSV validation."""
    
    def test_valid_csv(self):
        """Test validation with valid CSV."""
        df = pd.DataFrame({
            'site_id': ['A', 'B', 'C'],
            'lat': [40.0, 41.0, 42.0],
            'lon': [-74.0, -75.0, -76.0],
            'cluster_id': ['1', '1', '2']
        })
        df_clean, errors = validate_csv(df)
        assert len(df_clean) == 3
        assert len(errors) == 0
    
    def test_missing_columns(self):
        """Test validation with missing required columns."""
        df = pd.DataFrame({
            'site_id': ['A', 'B'],
            'lat': [40.0, 41.0]
        })
        df_clean, errors = validate_csv(df)
        assert len(df_clean) == 0
        assert any('Missing required columns' in err for err in errors)
    
    def test_missing_values(self):
        """Test validation drops rows with missing values."""
        df = pd.DataFrame({
            'site_id': ['A', 'B', 'C'],
            'lat': [40.0, None, 42.0],
            'lon': [-74.0, -75.0, None],
            'cluster_id': ['1', '1', '2']
        })
        df_clean, errors = validate_csv(df)
        assert len(df_clean) == 1
        assert df_clean.iloc[0]['site_id'] == 'A'
    
    def test_invalid_coordinates(self):
        """Test validation drops rows with invalid coordinates."""
        df = pd.DataFrame({
            'site_id': ['A', 'B', 'C'],
            'lat': [40.0, 91.0, -91.0],  # Invalid latitudes
            'lon': [-74.0, -75.0, -76.0],
            'cluster_id': ['1', '1', '2']
        })
        df_clean, errors = validate_csv(df)
        assert len(df_clean) == 1
        assert df_clean.iloc[0]['site_id'] == 'A'


class TestHaversineDistance:
    """Tests for Haversine distance calculation."""
    
    def test_same_point(self):
        """Distance from point to itself should be 0."""
        lat = np.array([40.0])
        lon = np.array([-74.0])
        distance = haversine_distance(lat, lon, lat, lon)
        assert distance[0] == pytest.approx(0.0, abs=1e-6)
    
    def test_known_distance(self):
        """Test with known distance (NYC to Philadelphia ~160km)."""
        # NYC coordinates
        lat1 = np.array([40.7128])
        lon1 = np.array([-74.0060])
        # Philadelphia coordinates
        lat2 = np.array([39.9526])
        lon2 = np.array([-75.1652])
        
        distance = haversine_distance(lat1, lon1, lat2, lon2)
        # Expected distance is approximately 160km
        assert distance[0] == pytest.approx(160.0, abs=10.0)
    
    def test_array_input(self):
        """Test with array inputs."""
        lat1 = np.array([40.0, 41.0])
        lon1 = np.array([-74.0, -75.0])
        lat2 = np.array([40.1, 41.1])
        lon2 = np.array([-74.1, -75.1])
        
        distances = haversine_distance(lat1, lon1, lat2, lon2)
        assert len(distances) == 2
        assert all(d > 0 for d in distances)


class TestDensityCalculation:
    """Tests for density calculation."""
    
    def test_single_point(self):
        """Single point should have density 0 (no neighbors)."""
        df = pd.DataFrame({
            'lat': [40.0],
            'lon': [-74.0]
        })
        density = calculate_density(df, radius_km=2.0)
        assert len(density) == 1
        assert density.iloc[0] == 0.0
    
    def test_three_points_in_line(self):
        """
        MANDATORY TEST: 3 synthetic points in a line.
        
        Points are placed 1km apart in a straight line.
        With radius=2km, each point should have 2 neighbors (excluding self).
        Density = 2 / (π * 2²) = 2 / (4π) ≈ 0.159 sites/km²
        """
        # Create 3 points in a line, 1km apart
        # Starting point: (40.0, -74.0)
        # Each degree of latitude ≈ 111km, so 1km ≈ 0.009 degrees
        # For longitude, we need to account for latitude: 1km ≈ 0.009 / cos(lat) degrees
        
        base_lat = 40.0
        base_lon = -74.0
        km_per_degree_lat = 111.0
        km_per_degree_lon = 111.0 * np.cos(np.radians(base_lat))
        
        # Points 1km apart (north-south line)
        df = pd.DataFrame({
            'site_id': ['A', 'B', 'C'],
            'lat': [
                base_lat - 1.0 / km_per_degree_lat,  # 1km south
                base_lat,                             # center
                base_lat + 1.0 / km_per_degree_lat    # 1km north
            ],
            'lon': [base_lon, base_lon, base_lon],
            'cluster_id': ['1', '1', '1']
        })
        
        radius_km = 2.0
        density = calculate_density(df, radius_km=radius_km)
        
        # Each point should have 2 neighbors within 2km radius
        # (the other 2 points are 1km away, which is < 2km)
        expected_neighbors = 2
        area_km2 = np.pi * (radius_km ** 2)
        expected_density = expected_neighbors / area_km2
        
        # Verify density for all points
        for i in range(3):
            assert density.iloc[i] == pytest.approx(expected_density, abs=1e-3), \
                f"Point {i} density mismatch: got {density.iloc[i]}, expected {expected_density}"
        
        # Verify neighbor counts by checking distances
        from backend.spatial_index import haversine_distance
        for i in range(3):
            neighbors_within_radius = 0
            for j in range(3):
                if i != j:
                    dist = haversine_distance(
                        np.array([df.iloc[i]['lat']]),
                        np.array([df.iloc[i]['lon']]),
                        np.array([df.iloc[j]['lat']]),
                        np.array([df.iloc[j]['lon']])
                    )[0]
                    if dist <= radius_km:
                        neighbors_within_radius += 1
            
            # Verify neighbor count matches density calculation
            calculated_density = neighbors_within_radius / area_km2
            assert density.iloc[i] == pytest.approx(calculated_density, abs=1e-6)
    
    def test_isolated_points(self):
        """Points far apart should have density 0."""
        df = pd.DataFrame({
            'lat': [40.0, 50.0, 60.0],  # Very far apart
            'lon': [-74.0, -75.0, -76.0]
        })
        density = calculate_density(df, radius_km=2.0)
        assert all(d == 0.0 for d in density)
    
    def test_clustered_points(self):
        """Clustered points should have high density."""
        # Create 10 points very close together (< 100m)
        base_lat = 40.0
        base_lon = -74.0
        km_per_degree = 111.0
        
        # Random points within 100m (0.1km)
        np.random.seed(42)  # For reproducibility in test
        offsets = np.random.uniform(-0.1/km_per_degree, 0.1/km_per_degree, (10, 2))
        
        df = pd.DataFrame({
            'lat': [base_lat + off[0] for off in offsets],
            'lon': [base_lon + off[1] for off in offsets]
        })
        
        density = calculate_density(df, radius_km=2.0)
        
        # Each point should have 9 neighbors (10 total - 1 self)
        expected_neighbors = 9
        area_km2 = np.pi * (2.0 ** 2)
        expected_density = expected_neighbors / area_km2
        
        # All points should have approximately the same density
        assert all(d == pytest.approx(expected_density, abs=1e-3) for d in density)


class TestCoLocationGroups:
    """Tests for co-location grouping."""
    
    def test_single_point(self):
        """Single point should form its own group."""
        df = pd.DataFrame({
            'site_id': ['A'],
            'lat': [40.0],
            'lon': [-74.0]
        })
        group_id, group_size = find_co_location_groups(df, threshold_m=100.0)
        assert len(group_id) == 1
        assert group_size.iloc[0] == 1
    
    def test_three_points_in_line_co_location(self):
        """Test co-location with 3 points in a line."""
        # Same setup as density test
        base_lat = 40.0
        base_lon = -74.0
        km_per_degree_lat = 111.0
        
        # Points 50m apart (should be in same group with 100m threshold)
        df = pd.DataFrame({
            'site_id': ['A', 'B', 'C'],
            'lat': [
                base_lat - 0.05 / km_per_degree_lat,  # 50m south
                base_lat,                             # center
                base_lat + 0.05 / km_per_degree_lat   # 50m north
            ],
            'lon': [base_lon, base_lon, base_lon]
        })
        
        group_id, group_size = find_co_location_groups(df, threshold_m=100.0)
        
        # All 3 points should be in the same group
        assert len(group_id.unique()) == 1
        assert all(group_size == 3)
    
    def test_separate_groups(self):
        """Points far apart should form separate groups."""
        df = pd.DataFrame({
            'site_id': ['A', 'B', 'C'],
            'lat': [40.0, 41.0, 42.0],  # Very far apart
            'lon': [-74.0, -75.0, -76.0]
        })
        group_id, group_size = find_co_location_groups(df, threshold_m=100.0)
        assert len(group_id.unique()) == 3
        assert all(group_size == 1)
    
    def test_deterministic_group_ids(self):
        """Group IDs should be deterministic (same members = same ID)."""
        base_lat = 40.0
        base_lon = -74.0
        km_per_degree = 111.0
        
        # Create two groups of 2 points each
        df = pd.DataFrame({
            'site_id': ['A', 'B', 'C', 'D'],
            'lat': [
                base_lat,
                base_lat + 0.05 / km_per_degree,  # Group 1
                base_lat + 1.0,                    # Far away
                base_lat + 1.0 + 0.05 / km_per_degree  # Group 2
            ],
            'lon': [base_lon, base_lon, base_lon, base_lon]
        })
        
        group_id, group_size = find_co_location_groups(df, threshold_m=100.0)
        
        # Should have 2 groups
        assert len(group_id.unique()) == 2
        # Each group should have size 2
        assert all(group_size == 2)
        # Same group members should have same group_id
        assert group_id.iloc[0] == group_id.iloc[1]  # A and B
        assert group_id.iloc[2] == group_id.iloc[3]  # C and D
        assert group_id.iloc[0] != group_id.iloc[2]  # Different groups


class TestClassification:
    """Tests for site classification."""
    
    def test_quantile_mode(self):
        """Test quantile-based classification."""
        df = pd.DataFrame({
            'density': [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
            'cluster_id': ['1'] * 8
        })
        
        area_class = classify_sites(df, mode='quantile')
        
        # Should have 4 classes
        assert set(area_class.unique()) == {'Rural', 'Suburban', 'Urban', 'Dense'}
        # Check distribution (2 points per quartile)
        assert (area_class == 'Rural').sum() == 2
        assert (area_class == 'Suburban').sum() == 2
        assert (area_class == 'Urban').sum() == 2
        assert (area_class == 'Dense').sum() == 2
    
    def test_quantile_mode_per_cluster(self):
        """Test quantile classification per cluster."""
        df = pd.DataFrame({
            'density': [1.0, 2.0, 3.0, 4.0, 10.0, 20.0, 30.0, 40.0],
            'cluster_id': ['1'] * 4 + ['2'] * 4
        })
        
        area_class = classify_sites(df, mode='quantile')
        
        # Each cluster should have all 4 classes
        cluster1_classes = area_class[df['cluster_id'] == '1']
        cluster2_classes = area_class[df['cluster_id'] == '2']
        
        assert set(cluster1_classes.unique()) == {'Rural', 'Suburban', 'Urban', 'Dense'}
        assert set(cluster2_classes.unique()) == {'Rural', 'Suburban', 'Urban', 'Dense'}
    
    def test_threshold_mode(self):
        """Test threshold-based classification."""
        df = pd.DataFrame({
            'density': [5.0, 25.0, 100.0, 300.0],
            'cluster_id': ['1'] * 4
        })
        
        thresholds = {
            'rural': 10.0,
            'suburban': 50.0,
            'urban': 200.0
        }
        
        area_class = classify_sites(df, mode='threshold', thresholds=thresholds)
        
        assert area_class.iloc[0] == 'Rural'      # 5.0 <= 10.0
        assert area_class.iloc[1] == 'Suburban'   # 10.0 < 25.0 <= 50.0
        assert area_class.iloc[2] == 'Urban'      # 50.0 < 100.0 <= 200.0
        assert area_class.iloc[3] == 'Dense'      # 300.0 > 200.0


class TestFullPipeline:
    """Tests for complete processing pipeline."""
    
    def test_full_pipeline(self):
        """Test complete processing pipeline."""
        df = pd.DataFrame({
            'site_id': ['A', 'B', 'C', 'D'],
            'lat': [40.0, 40.01, 40.02, 50.0],
            'lon': [-74.0, -74.0, -74.0, -75.0],
            'cluster_id': ['1', '1', '1', '2']
        })
        
        result_df, messages = process_sites(
            df,
            radius_km=2.0,
            co_location_threshold_m=1000.0,  # 1km threshold
            classification_mode='quantile'
        )
        
        # Check all required columns are present
        required_cols = ['site_id', 'lat', 'lon', 'cluster_id', 'density', 
                        'group_id', 'group_size', 'area_class']
        assert all(col in result_df.columns for col in required_cols)
        
        # Check all rows processed
        assert len(result_df) == 4
        
        # Check density is calculated
        assert 'density' in result_df.columns
        assert all(result_df['density'] >= 0)
        
        # Check classification
        assert all(result_df['area_class'].isin(['Rural', 'Suburban', 'Urban', 'Dense']))
    
    def test_empty_dataframe(self):
        """Test pipeline with empty DataFrame."""
        df = pd.DataFrame(columns=['site_id', 'lat', 'lon', 'cluster_id'])
        result_df, messages = process_sites(df)
        assert len(result_df) == 0
        assert any('No valid rows' in msg for msg in messages)
