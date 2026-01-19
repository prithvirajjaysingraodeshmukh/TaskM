"""
FastAPI application entry point.

Thin API layer that handles HTTP requests, parameter parsing, and response formatting.
All business logic is delegated to the pipeline module.
"""

import logging
from typing import Optional, Dict
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import pandas as pd
import io

from backend.schemas import AnalysisResponse, AnalysisSummary
from backend.pipeline import process_sites
from backend.utils import dataframe_to_csv_bytes, dataframe_to_dict_list

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Site Analysis API",
    description="AI/ML Intern Take-Home Assignment - Site Density and Classification API",
    version="1.0.0"
)

# Configure CORS for Docker (allow all origins for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Site Analysis API is running"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


def _parse_classification_thresholds(
    classification_mode: str,
    rural_threshold: Optional[float],
    suburban_threshold: Optional[float],
    urban_threshold: Optional[float]
) -> Optional[Dict[str, float]]:
    """
    Parse classification thresholds from query parameters.
    
    Returns None if not in threshold mode or no thresholds provided.
    """
    if classification_mode != "threshold":
        return None
    
    if rural_threshold is None and suburban_threshold is None and urban_threshold is None:
        return None
    
    thresholds = {}
    if rural_threshold is not None:
        thresholds['rural'] = rural_threshold
    if suburban_threshold is not None:
        thresholds['suburban'] = suburban_threshold
    if urban_threshold is not None:
        thresholds['urban'] = urban_threshold
    
    return thresholds


async def _read_csv_file(file: UploadFile) -> pd.DataFrame:
    """
    Read and parse CSV file from upload.
    
    Raises HTTPException on validation errors.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV file")
    
    contents = await file.read()
    
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading CSV: {str(e)}")
    
    if len(df) == 0:
        raise HTTPException(status_code=400, detail="CSV file is empty")
    
    return df


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_sites(
    file: UploadFile = File(..., description="CSV file with site data"),
    radius_km: float = Query(default=2.0, ge=0.1, le=100.0, description="Radius for density calculation (km)"),
    co_location_threshold_m: float = Query(default=100.0, ge=1.0, le=10000.0, description="Co-location threshold (meters)"),
    classification_mode: str = Query(default="quantile", pattern="^(quantile|threshold)$", description="Classification mode"),
    rural_threshold: Optional[float] = Query(default=None, ge=0.0, description="Rural threshold (for threshold mode)"),
    suburban_threshold: Optional[float] = Query(default=None, ge=0.0, description="Suburban threshold (for threshold mode)"),
    urban_threshold: Optional[float] = Query(default=None, ge=0.0, description="Urban threshold (for threshold mode)")
):
    """
    Analyze sites from uploaded CSV file.
    
    Required CSV columns: site_id, lat, lon, cluster_id
    
    Returns:
        Analysis results with summary, preview, and download URL
    """
    try:
        # Read and validate file
        df = await _read_csv_file(file)
        logger.info(f"Processing {len(df)} rows from file: {file.filename}")
        
        # Parse classification thresholds
        classification_thresholds = _parse_classification_thresholds(
            classification_mode, rural_threshold, suburban_threshold, urban_threshold
        )
        
        # Process sites using pipeline
        result_df, messages = process_sites(
            df=df,
            radius_km=radius_km,
            co_location_threshold_m=co_location_threshold_m,
            classification_mode=classification_mode,
            classification_thresholds=classification_thresholds
        )
        
        if len(result_df) == 0:
            raise HTTPException(
                status_code=400,
                detail="No valid rows after processing. Check CSV format and data quality."
            )
        
        # Calculate summary statistics
        area_class_counts = result_df['area_class'].value_counts().to_dict()
        summary = AnalysisSummary(
            Rural=area_class_counts.get('Rural', 0),
            Suburban=area_class_counts.get('Suburban', 0),
            Urban=area_class_counts.get('Urban', 0),
            Dense=area_class_counts.get('Dense', 0)
        )
        
        # Create preview (first 50 rows)
        preview = dataframe_to_dict_list(result_df, max_rows=50)
        
        # Generate download URL (simulated - in production, this would be a real URL)
        download_url = "/download"
        
        return AnalysisResponse(
            summary=summary,
            preview=preview,
            total_rows=len(result_df),
            messages=messages,
            download_url=download_url
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/download")
async def download_results(
    file: UploadFile = File(..., description="CSV file with site data"),
    radius_km: float = Query(default=2.0, ge=0.1, le=100.0),
    co_location_threshold_m: float = Query(default=100.0, ge=1.0, le=10000.0),
    classification_mode: str = Query(default="quantile", pattern="^(quantile|threshold)$"),
    rural_threshold: Optional[float] = Query(default=None, ge=0.0),
    suburban_threshold: Optional[float] = Query(default=None, ge=0.0),
    urban_threshold: Optional[float] = Query(default=None, ge=0.0)
):
    """
    Download full analysis results as CSV.
    
    Note: In a production system, this would use a job queue and store results.
    For this implementation, we reprocess the file with the same parameters.
    """
    try:
        # Read and validate file
        df = await _read_csv_file(file)
        
        # Parse classification thresholds
        classification_thresholds = _parse_classification_thresholds(
            classification_mode, rural_threshold, suburban_threshold, urban_threshold
        )
        
        # Process sites
        result_df, _ = process_sites(
            df=df,
            radius_km=radius_km,
            co_location_threshold_m=co_location_threshold_m,
            classification_mode=classification_mode,
            classification_thresholds=classification_thresholds
        )
        
        # Convert to CSV bytes
        csv_bytes = dataframe_to_csv_bytes(result_df)
        
        return Response(
            content=csv_bytes,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=analysis_results.csv"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating download: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating download: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
