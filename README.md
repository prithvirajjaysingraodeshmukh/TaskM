# Site Analysis Dashboard

A production-grade solution for AI/ML Intern Take-Home Assignment. This application analyzes site density, performs co-location grouping, and classifies sites into Rural, Suburban, Urban, and Dense categories.

## Architecture Overview

### Tech Stack

**Backend:**
- Python 3.11
- FastAPI (REST API framework)
- Pandas (Data processing)
- Scikit-Learn BallTree (Spatial indexing)
- SciPy (Graph algorithms for connected components)
- NumPy (Numerical computations)
- Pydantic (Data validation)

**Frontend:**
- React 18 (UI framework)
- TypeScript (Type safety)
- Material UI (Component library)
- Leaflet & React-Leaflet (Geographic map visualization)
- React-Leaflet-Cluster (Marker clustering for performance)
- Vite (Build tool)

**Infrastructure:**
- Docker & Docker Compose
- Nginx (Frontend serving)
- Uvicorn (ASGI server)

### Project Structure

```
TasKK/
├── backend/
│   ├── main.py              # FastAPI application entry point (thin API layer)
│   ├── pipeline.py          # Processing pipeline orchestration
│   ├── validator.py         # CSV & data validation logic
│   ├── spatial_index.py     # BallTree construction & coordinate conversion
│   ├── neighbors.py         # Neighbor count & density computation
│   ├── colocation.py        # Co-location grouping (connected components)
│   ├── classifier.py        # Area classification (quantile + threshold)
│   ├── schemas.py           # Pydantic models for validation
│   ├── utils.py             # Utility functions (CSV conversion, etc.)
│   ├── tests/
│   │   └── test_logic.py    # Comprehensive unit tests
│   ├── requirements.txt     # Python dependencies
│   ├── Dockerfile           # Backend container
│   └── pytest.ini           # Test configuration
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Main application component
│   │   ├── theme.ts         # Material UI theme configuration
│   │   ├── components/      # React components
│   │   │   ├── ConfigurationPanel.tsx
│   │   │   ├── Dashboard.tsx
│   │   │   └── SiteMap.tsx  # Leaflet map component with clustering
│   │   ├── api/
│   │   │   └── client.ts    # API client
│   │   └── types.ts         # TypeScript types
│   ├── package.json
│   ├── Dockerfile           # Multi-stage frontend build
│   └── nginx.conf           # Nginx configuration
├── docker-compose.yml       # Service orchestration
└── README.md
```

## Core Algorithm: Why BallTree?

### Spatial Indexing Performance

The application uses **scikit-learn's BallTree** for spatial neighbor queries instead of brute-force O(N²) distance calculations.

**Time Complexity:**
- **Brute Force:** O(N²) - For each point, calculate distance to all other points
- **BallTree:** O(N log N) construction + O(N log N) queries = **O(N log N) overall**

**Why BallTree over KD-Tree?**
- BallTree supports **Haversine distance** (great-circle distance on a sphere)
- KD-Tree only works with Euclidean distance, which is inaccurate for geographic coordinates
- BallTree is specifically designed for metric spaces, making it ideal for geographic data

**Example Performance:**
- 1,000 sites: Brute force ~1M operations vs BallTree ~10K operations
- 10,000 sites: Brute force ~100M operations vs BallTree ~130K operations
- 100,000 sites: Brute force ~10B operations vs BallTree ~1.3M operations

### Density Calculation

Density is calculated as:
```
density = (number of neighbors within radius) / (π × radius²)
```

**Key Points:**
- Neighbors exclude the point itself
- Radius is user-configurable (default: 2km)
- Units: sites per km²

### Co-location Grouping

Uses **graph-based connected components** algorithm with SciPy:

1. Build a sparse adjacency matrix where edges exist if distance < threshold
2. Find connected components using SciPy's `connected_components` (Union-Find algorithm)
3. Generate deterministic `group_id` as hash of sorted member site_ids
4. Calculate `group_size` for each group

**Why SciPy Connected Components?**
- Non-recursive algorithm (avoids stack overflow with large datasets)
- Efficient Union-Find implementation (near-linear time complexity)
- Handles 100k+ sites without recursion depth issues

**Deterministic Group IDs:**
- Same members → Same group_id (regardless of processing order)
- Uses hash of sorted tuple of site_ids

### Classification

Two modes available:

1. **Quantile Mode (default):**
   - Calculates percentiles (25th, 50th, 75th) **per cluster_id**
   - Ensures fair distribution across clusters
   - Rural ≤ Q25, Suburban (Q25, Q50], Urban (Q50, Q75], Dense > Q75

2. **Threshold Mode:**
   - Uses fixed density thresholds
   - Configurable via API parameters
   - Default: Rural ≤ 10, Suburban (10, 50], Urban (50, 200], Dense > 200 sites/km²

## Running the Application

### Prerequisites

- Docker and Docker Compose installed
- OR Python 3.11+ and Node.js 18+ for local development

### Quick Start with Docker

```bash
# Build and start all services
docker compose up --build

# Access the application
# Frontend: http://localhost:8501
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Local Development

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
# Frontend will run on http://localhost:5173
```

### Running Tests

```bash
cd backend
pip install -r requirements.txt
pytest tests/test_logic.py -v
```

**Mandatory Test:**
```bash
pytest tests/test_logic.py::TestDensityCalculation::test_three_points_in_line -v
```

This test verifies:
- 3 points placed 1km apart in a line
- With 2km radius, each point has 2 neighbors
- Density = 2 / (π × 2²) ≈ 0.159 sites/km²

## API Endpoints

### POST /analyze

Analyze sites from uploaded CSV file.

**Request:**
- Multipart form data with CSV file
- Query parameters:
  - `radius_km` (float, default: 2.0)
  - `co_location_threshold_m` (float, default: 100.0)
  - `classification_mode` (string: "quantile" | "threshold")
  - `rural_threshold`, `suburban_threshold`, `urban_threshold` (optional, for threshold mode)

**Response:**
```json
{
  "summary": {
    "Rural": 10,
    "Suburban": 5,
    "Urban": 3,
    "Dense": 2
  },
  "preview": [...],
  "total_rows": 20,
  "messages": [...],
  "download_url": "/download"
}
```

### POST /download

Download full analysis results as CSV.

**Request:** Same as `/analyze`

**Response:** CSV file download

### GET /health

Health check endpoint.

## CSV Format

Required columns:
- `site_id` (string): Unique identifier
- `lat` (float): Latitude (-90 to 90)
- `lon` (float): Longitude (-180 to 180)
- `cluster_id` (string): Cluster identifier

**Example:**
```csv
site_id,lat,lon,cluster_id
A,40.7128,-74.0060,1
B,40.7580,-73.9855,1
C,40.7489,-73.9680,2
```

## Design Decisions

### 1. Modular Backend Architecture

The backend is organized into focused modules with single responsibilities:

- **main.py**: Thin API layer - handles HTTP requests, parameter parsing, response formatting
- **pipeline.py**: Orchestrates the full processing workflow
- **validator.py**: CSV structure and data validation
- **spatial_index.py**: BallTree construction, coordinate conversion, Haversine distance
- **neighbors.py**: Neighbor counting and density calculation
- **colocation.py**: Graph-based co-location grouping using connected components
- **classifier.py**: Area classification logic (quantile and threshold modes)
- **schemas.py**: Pydantic models for request/response validation
- **utils.py**: Utility functions for data conversion

This modular structure provides:
- Clear separation of concerns
- Easy testing of individual components
- Maintainable and extensible codebase

### 2. Deterministic Logic

- No random seeds in production code
- Deterministic group IDs (hash of sorted members)
- Reproducible results for same input

### 3. Defensive Validation

- Comprehensive CSV validation
- Detailed error messages
- Graceful handling of invalid data

### 4. Standard Libraries

- No "clever" hacks
- Industry-standard tools (Pydantic, FastAPI, MUI, Leaflet)
- Well-documented and maintainable

### 5. Frontend Architecture

- **Modern SaaS UI**: Material UI with custom theme for professional appearance
- **Geographic Visualization**: Leaflet maps with marker clustering for 100k+ points
- **Client-Side CSV Export**: Efficient browser-based CSV generation
- **Responsive Layout**: Grid-based layout with configuration panel and results area
- **TypeScript**: Full type safety throughout

## Performance Optimizations

### Backend

- **BallTree**: O(N log N) spatial queries (vs O(N²) brute force)
- **SciPy Connected Components**: Non-recursive Union-Find algorithm for large datasets
- **Sparse Matrices**: Memory-efficient graph representation for co-location
- **Vectorized Operations**: NumPy/Pandas for efficient data processing
- **Handles 100k+ sites**: Tested and optimized for large datasets

### Frontend

- **Marker Clustering**: React-Leaflet-Cluster with `chunkedLoading` for 100k+ markers
- **Client-Side CSV Export**: Efficient array-based string building
- **Pagination**: Client-side pagination for data table preview
- **Lazy Loading**: Components load only when needed

## Testing

The test suite includes:

1. **Validation Tests**: CSV structure and data quality
2. **Haversine Distance Tests**: Geographic distance calculations
3. **Density Calculation Tests**: Including mandatory 3-point line test
4. **Co-location Tests**: Graph-based grouping verification
5. **Classification Tests**: Both quantile and threshold modes
6. **Integration Tests**: Full pipeline end-to-end

## Future Enhancements

- Job queue for large file processing (Celery/Redis)
- Result caching with Redis
- WebSocket for real-time progress updates
- Batch processing API
- Authentication and authorization
- Database persistence for results
- Streaming processing for very large files (>1M rows)

## License

This is a take-home assignment solution. All code is provided for evaluation purposes.
