import os
import shutil
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from core.settings_manager import (
    get_model, has_api_key,
    update_model, update_api_key,
    get_max_scan_files, update_max_scan_files,
)

router = APIRouter(prefix="/settings", tags=["settings"])

class ModelRequest(BaseModel):
    model: str

class ApiKeyRequest(BaseModel):
    api_key: str

class MaxScanFilesRequest(BaseModel):
    max_scan_files: int

# --- Model ---
@router.get("/model")
def get_model_setting():
    return {"model": get_model()}

@router.post("/model")
def update_model_setting(req: ModelRequest):
    update_model(req.model)
    return {"status": "success", "model": get_model()}

# --- API Key ---
@router.get("/api-key")
def get_api_key_setting():
    return {"api_key_set": has_api_key()}

@router.post("/api-key")
def update_api_key_setting(req: ApiKeyRequest):
    update_api_key(req.api_key)
    return {"status": "success", "api_key_set": has_api_key()}

# --- Max Scan Files ---
@router.get("/max-scan-files")
def get_max_scan_files_setting():
    return {"max_scan_files": get_max_scan_files()}

@router.post("/max-scan-files")
def update_max_scan_files_setting(req: MaxScanFilesRequest):
    update_max_scan_files(req.max_scan_files)
    return {"status": "success", "max_scan_files": get_max_scan_files()}
