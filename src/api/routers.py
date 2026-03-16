from fastapi import APIRouter, File, UploadFile, BackgroundTasks, Form
from typing import List, Optional
import shutil
import uuid
import os
import json

from src.services.ingestion import ingestion_service
from src.services.analysis import analysis_engine
from src.engine.decision import decision_engine
from src.pipeline.indexer import indexer_service
from src.runtime.rag import rag_runtime

api_router = APIRouter()

@api_router.get("/health", tags=["system"])
def health_check():
    return {"status": "ok", "message": "AutoRAG Architect system is running"}

@api_router.post("/projects/build", tags=["pipeline"])
async def build_pipeline(
    background_tasks: BackgroundTasks, 
    files: List[UploadFile] = File(...),
    api_keys: Optional[str] = Form(None)
):
    """Receives files, makes architectural decisions, and starts the indexing pipeline."""
    project_id = str(uuid.uuid4())
    upload_dir = os.path.join(os.getcwd(), "uploads", project_id)
    os.makedirs(upload_dir, exist_ok=True)
    
    saved_files = []
    for file in files:
        file_location = os.path.join(upload_dir, file.filename)
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
        saved_files.append(file_location)
        
    dataset_metrics = []
    documents = []
    for path in saved_files:
        try:
            doc_data = ingestion_service.ingest_file(path)
            documents.append(doc_data)
            metrics = analysis_engine.analyze_document(doc_data)
            dataset_metrics.append(metrics)
        except Exception as e:
            print(f"Failed to process {path}: {e}")
            
    if not dataset_metrics:
        return {"error": "No valid documents could be processed."}
        
    # Parse API keys if provided
    parsed_keys = {}
    if api_keys:
        try:
            parsed_keys = json.loads(api_keys)
        except Exception as e:
            print(f"Failed to parse api_keys: {e}")

    # Run AI Architect Decision Engine with optional LLM intelligence
    architecture = decision_engine.determine_architecture(dataset_metrics, api_keys=parsed_keys)
    
    # Run Indexing in background to free up API response
    background_tasks.add_task(indexer_service.execute_pipeline, project_id, architecture, documents)
    
    return {
        "project_id": project_id,
        "message": "Files analyzed and indexing started.",
        "architecture_decision": architecture,
        "dataset_analysis": dataset_metrics
    }

@api_router.get("/projects", tags=["pipeline"])
def list_projects():
    """Lists all active deployments."""
    chroma_dir = os.path.join(os.getcwd(), "chroma_db")
    if not os.path.exists(chroma_dir):
        return {"projects": []}
        
    projects = []
    for d in os.listdir(chroma_dir):
        metadata_path = os.path.join(chroma_dir, d, "metadata.json")
        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as f:
                projects.append(json.load(f))
                
    # Sort by created_at descending
    projects.sort(key=lambda x: x.get("created_at", 0), reverse=True)
    return {"projects": projects}

from pydantic import BaseModel
class QueryRequest(BaseModel):
    query: str
    architecture: dict

@api_router.post("/projects/{project_id}/query", tags=["pipeline"])
def query_pipeline(project_id: str, request: QueryRequest):
    """Queries an indexed project pipeline."""
    response = rag_runtime.generate_response(project_id, request.query, request.architecture)
    return response

