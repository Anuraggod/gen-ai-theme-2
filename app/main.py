"""
main.py - FastAPI application for the Smart Guided Troubleshooting Engine.
Exposes REST API endpoints and mounts the demonstration UI.
"""

import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.schema import TroubleshootRequest, TroubleshootResponse, HealthResponse
from app.engine.pipeline import TroubleshootingPipeline
from app.config import SERVICE_NAME, SERVICE_VERSION

app = FastAPI(
    title=SERVICE_NAME,
    version=SERVICE_VERSION,
    description="Smart Guided Troubleshooting Engine REST API Service (Theme 2)"
)

# Enable CORS for demonstration frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize pipeline
pipeline = TroubleshootingPipeline()

# Mount static directory for interactive demo UI
STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": f"{SERVICE_NAME} API is running. Access /docs for API documentation."}


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def get_health():
    """
    Service health check endpoint.
    """
    return HealthResponse(
        status="ok",
        service=SERVICE_NAME,
        version=SERVICE_VERSION,
        catalog_items_loaded=len(pipeline.deeplink_mapper.catalog),
        cache_size=pipeline.cache.size()
    )


@app.post("/v1/troubleshoot", response_model=TroubleshootResponse, tags=["Troubleshooting"])
async def troubleshoot(request: TroubleshootRequest):
    """
    Processes natural-language customer queries and returns validated,
    grounded troubleshooting plans with exact catalog deeplinks.
    """
    if not request.query or not request.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query string cannot be empty."
        )

    try:
        response = pipeline.process_query(request)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing troubleshooting pipeline: {str(e)}"
        )


@app.get("/v1/catalog", tags=["Catalog"])
async def get_catalog():
    """
    Returns indexed device setting deeplink catalog metadata.
    """
    return {
        "catalog_size": len(pipeline.deeplink_mapper.catalog),
        "items": pipeline.deeplink_mapper.catalog
    }


@app.post("/v1/cache/clear", tags=["Cache"])
async def clear_cache():
    """
    Clears in-memory semantic cache.
    """
    pipeline.cache.clear()
    return {"status": "success", "message": "Fast-path semantic cache cleared."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
