import json
import os
import shutil
import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from src.core.exceptions import (
    AnalysisError,
    DecisionEngineError,
    FileSizeLimitError,
    IngestionError,
    UnsupportedFileTypeError,
)
from src.core.logging import get_logger
from src.core.schemas import (
    BuildPipelineResponse,
    QueryRequest,
)
from src.engine.decision import decision_engine
from src.pipeline.indexer import indexer_service
from src.runtime.rag import rag_runtime
from src.services.analysis import analysis_engine
from src.services.ingestion import MAX_FILE_SIZE_BYTES, ingestion_service

logger = get_logger(__name__)

api_router = APIRouter()

# Allowed MIME types for upload (defence-in-depth alongside extension check)
_ALLOWED_MIME_PREFIXES = (
    "text/",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument",
    "application/json",
    "application/octet-stream",  # fallback for binary formats
)


def _safe_filename(filename: str | None) -> str:
    """Sanitise an uploaded filename to prevent path-traversal attacks.

    Strips directory components and any leading dots/slashes so that the
    caller-controlled *filename* cannot escape the upload directory.
    """
    if not filename:
        return "upload"
    # os.path.basename handles both / and \\ separators
    name = os.path.basename(filename)
    # Strip remaining leading dots that could create hidden files
    name = name.lstrip(".")
    return name or "upload"


@api_router.get("/health", tags=["system"])
def health_check():
    return {"status": "ok", "message": "AutoRAG Architect is running"}


@api_router.post("/projects/build", response_model=BuildPipelineResponse, tags=["pipeline"])
async def build_pipeline(
    background_tasks: BackgroundTasks,
    files: Annotated[list[UploadFile], File(description="Files to ingest")],
    api_keys: Annotated[str | None, Form(description="JSON API keys")] = None,
):
    """Analyse uploaded documents, run the architecture decision engine, and start indexing.

    Files are saved to ``uploads/<project_id>/`` on disk.  Indexing is
    executed in a background task so the endpoint returns immediately with
    the architecture decision and per-file analysis.

    The *api_keys* form field, if provided, must be a JSON string with the
    keys ``llm_provider``, ``llm_key``, ``vector_db_provider``, and
    ``embedding_provider``.

    > ⚠️  **Security note**: API keys should be stored server-side in a future
    > iteration (Phase 2) rather than transmitted per-request.
    """
    project_id = str(uuid.uuid4())
    upload_dir = os.path.join(os.getcwd(), "uploads", project_id)
    os.makedirs(upload_dir, exist_ok=True)

    saved_files: list[str] = []
    for upload in files:
        safe_name = _safe_filename(upload.filename)
        file_location = os.path.join(upload_dir, safe_name)

        # Read into memory to check size before writing to disk
        file_bytes = await upload.read()
        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            max_mb = MAX_FILE_SIZE_BYTES // (1024 * 1024)
            raise HTTPException(
                status_code=413,
                detail=f"File '{safe_name}' exceeds the {max_mb} MB upload limit.",
            )

        with open(file_location, "wb") as fh:
            fh.write(file_bytes)
        saved_files.append(file_location)
        logger.info("file_saved", project_id=project_id, filename=safe_name, bytes=len(file_bytes))

    # --- Ingestion + Analysis ---
    documents = []
    dataset_metrics = []
    errors: list[str] = []

    for path in saved_files:
        try:
            doc = ingestion_service.ingest_file(path)
            metrics = analysis_engine.analyze_document(doc)
            documents.append(doc)
            dataset_metrics.append(metrics)
        except UnsupportedFileTypeError as exc:
            logger.warning("unsupported_file_skipped", path=path, error=str(exc))
            errors.append(str(exc))
        except FileSizeLimitError as exc:
            logger.warning("oversized_file_skipped", path=path, error=str(exc))
            errors.append(str(exc))
        except IngestionError as exc:
            logger.error("ingestion_failed", path=path, error=str(exc))
            errors.append(str(exc))
        except AnalysisError as exc:
            logger.error("analysis_failed", path=path, error=str(exc))
            errors.append(str(exc))

    if not dataset_metrics:
        # Clean up the empty upload directory
        shutil.rmtree(upload_dir, ignore_errors=True)
        raise HTTPException(
            status_code=422,
            detail={
                "error": "No valid documents could be processed.",
                "file_errors": errors,
            },
        )

    # --- Parse API keys ---
    parsed_keys: dict = {}
    if api_keys:
        try:
            parsed_keys = json.loads(api_keys)
        except Exception:
            logger.warning("api_keys_parse_failed", project_id=project_id)

    # --- Architecture decision ---
    try:
        architecture = decision_engine.determine_architecture(
            [m.model_dump() for m in dataset_metrics],
            api_keys=parsed_keys,
        )
    except DecisionEngineError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    # --- Start background indexing ---
    background_tasks.add_task(indexer_service.execute_pipeline, project_id, architecture, documents)

    logger.info(
        "pipeline_build_initiated",
        project_id=project_id,
        documents=len(documents),
        errors=len(errors),
    )

    return BuildPipelineResponse(
        project_id=project_id,
        message="Files analysed and indexing started in background.",
        architecture_decision=architecture,
        dataset_analysis=dataset_metrics,
        errors=errors,
    )


@api_router.get("/projects", tags=["pipeline"])
def list_projects():
    """List all indexed projects with their metadata."""
    chroma_dir = os.path.join(os.getcwd(), "chroma_db")
    if not os.path.exists(chroma_dir):
        return {"projects": []}

    projects = []
    for d in os.listdir(chroma_dir):
        metadata_path = os.path.join(chroma_dir, d, "metadata.json")
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path) as f:
                    projects.append(json.load(f))
            except Exception as exc:
                logger.warning("metadata_read_failed", dir=d, error=str(exc))

    projects.sort(key=lambda x: x.get("created_at", 0), reverse=True)
    return {"projects": projects}


@api_router.post("/projects/{project_id}/query", tags=["pipeline"])
def query_pipeline(project_id: str, request: QueryRequest):
    """Query an indexed project and return an AI-generated answer with source context."""
    try:
        result = rag_runtime.generate_response(
            project_id=project_id,
            query_text=request.query,
            architecture_decision=request.architecture,
        )
    except Exception as exc:
        logger.error("query_failed", project_id=project_id, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    # Missing project returns a dict with an "error" key
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result
