import os
from fastapi import FastAPI, Request, HTTPException # Added HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse # Added FileResponse
import datetime
import json # For API endpoint returning JSON
from pathlib import Path # For API endpoints if they interact with paths

# This will be the new settings object, ensure src.config is compatible or updated.
from src.config import Settings
settings = Settings() # Use the actual settings for consistency

# Import logger after settings if logger uses settings
from src.logger import get_logger
logger = get_logger(__name__)


app = FastAPI(
    title="Iniity AI Agent API",
    description="Proprietary Anomaly Detection System by Iniity Inc.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    contact={
        "name": "Iniity Support",
        "url": "https://www.iniity.com/support",
        "email": "support@iniity.com",
    }
)

# Mount static files directory first, ensure 'static' dir exists at the root
# The Dockerfile creates /app/static, and docker-compose maps ./static to /app/static
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates, ensure 'templates' dir exists at the root
templates = Jinja2Templates(directory="templates")

# --- Root and Basic API Endpoints ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main dashboard"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/v1/health", response_class=JSONResponse)
async def health_check():
    """Health check endpoint"""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z", # Added Z for UTC
            "services": {
                "database": "available", # Placeholder status
                "ml_service": "available", # Placeholder status
                "storage": "available"     # Placeholder status
            },
            "version": app.version, # Use FastAPI app version
            "environment": settings.ENVIRONMENT
        }
    )

@app.get("/api/v1/info", response_class=JSONResponse)
async def system_info():
    """System information endpoint"""
    return {
        "system": "Iniity AI Agent",
        "version": app.version,
        "author": "Iniity Inc.",
        "license": "MIT",
        "repository": "https://git.iniity.com/IniitySovereignAgent.git"
    }

# Placeholder for future API endpoints from user's plan (Phase B2, C3 etc.)
# These will be filled in later steps. For example:
# from scripts.verify_integrity import verify_integrity as verify_script_main_func
# from scripts.verify_integrity import generate_manifest as generate_manifest_script_main_func

# @app.get("/api/v1/integrity", response_class=JSONResponse)
# async def get_integrity_status():
#     # This will call verify_script_main_func and return structured JSON
#     # Needs refactoring of verify_script_main_func to return data, not just print/exit
#     # For now, a placeholder:
#     try:
#         # success = verify_script_main_func() # This needs to be adapted
#         # For placeholder purposes:
#         is_verified = True # Assume true for now
#         failed_files = [] # if not is_verified
#         if is_verified:
#             return {"verified": True, "status_message": "Codebase integrity verified."}
#         else:
#             return JSONResponse(status_code=500, content={"verified": False, "status_message": "Codebase integrity check failed.", "failed_files": failed_files})
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @app.post("/api/v1/integrity/generate", response_class=JSONResponse) # Changed to POST as it's an action
# async def generate_integrity_manifest_api():
#     # This will call generate_manifest_script_main_func
#     # Needs refactoring of script for JSON return
#     try:
#         # manifest_content = generate_manifest_script_main_func() # This needs to be adapted
#         # For placeholder purposes:
#         manifest_content = {"status": "Generated placeholder manifest", "timestamp": datetime.datetime.utcnow().isoformat()}
#         return {"status": "success", "manifest": manifest_content}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# Placeholder for /api/v1/data/verify (from user's Phase B3)
# @app.get("/api/v1/data/verify", response_class=JSONResponse)
# async def verify_data_integrity_api():
#     # ... logic to call data/model verification ...
#     return {"verified": True, "details": "Data and models integrity placeholder."}


# --- API Endpoints for Code Integrity (Phase B2) ---
from scripts.verify_integrity import generate_manifest as generate_manifest_script
from scripts.verify_integrity import verify_integrity as verify_integrity_script

@app.get("/api/v1/integrity", response_class=JSONResponse)
async def get_integrity_status_api():
    """
    Verifies the integrity of the codebase against the sovereign_manifest.json.
    Returns a detailed verification status.
    """
    try:
        # project_root for the script, assuming API is run from project root context
        project_root = str(Path(".").resolve())
        verification_result = verify_integrity_script(project_root_str=project_root)
        if verification_result.get("error_message"):
            # If script itself had an error reading manifest etc.
            raise HTTPException(status_code=500, detail=verification_result["error_message"])
        return verification_result # This dict now contains {"verified": bool, "details": ...}
    except Exception as e:
        # Catch any other unexpected errors during the call
        logger.error(f"API /integrity: Error during verification: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error during integrity verification: {str(e)}")

@app.post("/api/v1/integrity/generate", response_class=JSONResponse) # Changed to POST
async def generate_integrity_manifest_api():
    """
    Generates a new sovereign_manifest.json for the codebase.
    Returns the generated manifest content.
    """
    try:
        project_root = str(Path(".").resolve())
        manifest_content = generate_manifest_script(project_root_str=project_root)
        if manifest_content:
            return {"status": "success", "message": "Manifest generated successfully.", "manifest": manifest_content}
        else:
            raise HTTPException(status_code=500, detail="Manifest generation failed (script returned None).")
    except Exception as e:
        logger.error(f"API /integrity/generate: Error during manifest generation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error during manifest generation: {str(e)}")

# Placeholder for /api/v1/export (from user's Phase C3)
# @app.get("/api/v1/export", response_class=FileResponse) # Or appropriate Response type
# async def export_manifest_api(format: str = "json"):
#     # ... logic for export ...
#     if format == "json":
#         # ... create and return JSON file
#         pass
#     elif format == "pdf":
#         # ... create and return PDF FileResponse
#         pass
#     raise HTTPException(status_code=400, detail="Invalid format")

# Placeholder for /api/v1/verify-export (from user's Phase C3)
# @app.post("/api/v1/verify-export", response_class=JSONResponse)
# async def verify_exported_manifest_api(request: Request):
#     # ... logic to verify uploaded/provided manifest ...
#     return {"verified": True, "details": "Export verification placeholder."}


# If running this file directly (though uvicorn command in Dockerfile/docker-compose is preferred)
if __name__ == "__main__":
    # This part is mostly for local dev outside Docker, or if someone runs python src/main.py
    # The CMD in Dockerfile is `uvicorn src.main:app --host 0.0.0.0 --port 8000`
    # The docker-compose command adds --reload.
    import uvicorn
    # Make sure to use the global `app` instance here, not a locally defined one
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True) # Added reload for local dev consistency
