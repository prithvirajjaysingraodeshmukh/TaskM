import pandas as pd
import numpy as np

# Configuration
# Change this line only:
NUM_SITES = 100000  # 100k rows
CLUSTERS = 100      # Increase clusters slightly

print(f"Generating {NUM_SITES} sites with {CLUSTERS} dense clusters...")

# 1. Generate Random "Rural" Noise (Background sites)
# Spread across a roughly 100km x 100km area
lat_noise = np.random.uniform(12.8, 13.8, NUM_SITES)
lon_noise = np.random.uniform(77.4, 78.4, NUM_SITES)

# 2. Generate "Dense" Clusters (Urban centers)
# We will overwrite the first 20% of points to be dense clusters
num_cluster_points = int(NUM_SITES * 0.2)
cluster_centers_lat = np.random.uniform(13.0, 13.5, CLUSTERS)
cluster_centers_lon = np.random.uniform(77.5, 78.0, CLUSTERS)

# Assign points to clusters
for i in range(num_cluster_points):
    cluster_idx = i % CLUSTERS
    # Gaussian distribution around the center (tight spread = dense)
    lat_noise[i] = cluster_centers_lat[cluster_idx] + np.random.normal(0, 0.005)
    lon_noise[i] = cluster_centers_lon[cluster_idx] + np.random.normal(0, 0.005)

# 3. Create DataFrame
df = pd.DataFrame({
    'site_id': [f'STRESS_{i:05d}' for i in range(NUM_SITES)],
    'lat': lat_noise,
    'lon': lon_noise,
    'cluster_id': 'TEST_REGION_1'
})

# 4. Save
filename = "limit_test.csv"
df.to_csv(filename, index=False)
print(f"✅ Created '{filename}'. Size: ~2.5 MB. Ready to upload!")