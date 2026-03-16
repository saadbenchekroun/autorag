"""CLI interface for AutoRAG Architect.

Install with:  pip install -e ".[cli]"
Run with:      autorag --help

Commands:
  autorag index <path>...       Ingest and index documents
  autorag query <project> TEXT  Query an indexed project
  autorag list                  List all indexed projects
  autorag serve                 Start the API server
"""

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="autorag",
    help="AutoRAG Architect — autonomous RAG pipeline builder",
    add_completion=False,
)
console = Console()


@app.command("index")
def index_documents(
    paths: Annotated[list[Path], typer.Argument(help="Files or directories to index")],
    api_keys_json: Annotated[
        str | None, typer.Option("--api-keys", help="JSON string with LLM/vector DB API keys")
    ] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
):
    """Ingest documents, run the architecture decision engine, and index them."""
    from src.core.logging import configure_logging
    from src.engine.decision import decision_engine
    from src.pipeline.indexer import indexer_service
    from src.services.analysis import analysis_engine
    from src.services.ingestion import ingestion_service

    configure_logging()

    # Resolve all file paths
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            files.extend(f for f in p.rglob("*") if f.is_file())
        else:
            files.append(p)

    if not files:
        console.print("[red]No files found.[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]Found {len(files)} file(s)[/bold]")

    documents = []
    metrics = []
    errors = []

    for f in files:
        try:
            doc = ingestion_service.ingest_file(str(f))
            m = analysis_engine.analyze_document(doc)
            documents.append(doc)
            metrics.append(m)
            if verbose:
                console.print(
                    f"  ✓ {f.name} — {m.estimated_tokens:,} tokens, "
                    f"density={m.semantic_density}, code={m.has_code_blocks}"
                )
        except Exception as e:
            errors.append(str(e))
            console.print(f"  [yellow]⚠ {f.name}: {e}[/yellow]")

    if not metrics:
        console.print("[red]No documents could be processed.[/red]")
        raise typer.Exit(1)

    api_keys = {}
    if api_keys_json:
        try:
            api_keys = json.loads(api_keys_json)
        except json.JSONDecodeError as exc:
            console.print("[red]Invalid JSON for --api-keys[/red]")
            raise typer.Exit(1) from exc

    console.print("\n[bold]Running architecture decision engine…[/bold]")
    decision = decision_engine.determine_architecture(
        [m.model_dump() for m in metrics], api_keys=api_keys
    )

    console.print(f"  Vector DB:  [cyan]{decision.vector_database}[/cyan]")
    console.print(
        f"  Chunking:   [cyan]{decision.chunking_strategy}[/cyan] "
        f"(size={decision.chunk_size}, overlap={decision.overlap_size})"
    )
    console.print(f"  Embedding:  [cyan]{decision.embedding_model}[/cyan]")
    for r in decision.reasoning:
        console.print(f"  → {r}")

    import uuid

    project_id = str(uuid.uuid4())
    console.print(f"\n[bold]Indexing project [cyan]{project_id}[/cyan]…[/bold]")

    result = indexer_service.execute_pipeline(project_id, decision, documents)
    console.print(
        f"[green]✔ Done! {result.chunks_created} chunks indexed.[/green]\n"
        f"  Project ID: {project_id}"
    )


@app.command("query")
def query_project(
    project_id: Annotated[str, typer.Argument(help="Project ID returned by 'autorag index'")],
    question: Annotated[str, typer.Argument(help="Natural-language question to ask")],
    vector_database: Annotated[
        str, typer.Option(help="Vector store used during indexing")
    ] = "chroma",
    embedding_model: Annotated[str, typer.Option(help="Embedding model used")] = "huggingface_bge",
    k: Annotated[int, typer.Option(help="Number of chunks to retrieve")] = 3,
):
    """Query an indexed project and display the answer with sources."""
    from src.core.schemas import ArchitectureDecision, QueryResponse
    from src.runtime.rag import rag_runtime

    decision = ArchitectureDecision(
        vector_database=vector_database,
        chunking_strategy="recursive_hierarchical",
        chunk_size=500,
        overlap_size=50,
        embedding_model=embedding_model,
    )

    result = rag_runtime.generate_response(project_id, question, decision, k=k)

    if isinstance(result, QueryResponse):
        console.print(f"\n[bold]Answer:[/bold]\n{result.answer}")
        if result.context_used:
            console.print(f"\n[dim]Sources: {len(result.context_used)} chunks retrieved[/dim]")
            for ctx in result.context_used:
                console.print(f"  [{ctx.source}] {ctx.text[:120]}…")
    elif isinstance(result, dict):
        ans = result.get("answer") or result.get("error", "No answer found.")
        console.print(f"\n[bold]Answer/Error:[/bold]\n{ans}")
        if "context_used" in result and isinstance(result["context_used"], list):
            console.print("[bold]Sources:[/bold]")
            for ctx_dict in result["context_used"]:
                if isinstance(ctx_dict, dict):
                    src = ctx_dict.get("source", "unknown")
                    txt = ctx_dict.get("text", "")[:120]
                    console.print(f"  [{src}] {txt}…")


@app.command("list")
def list_projects():
    """List all indexed projects."""
    import os
    import time

    chroma_dir = os.path.join(os.getcwd(), "chroma_db")
    if not os.path.exists(chroma_dir):
        console.print("No projects found.")
        return

    table = Table(title="AutoRAG Projects")
    table.add_column("Project ID", style="cyan")
    table.add_column("Vector DB")
    table.add_column("Chunks")
    table.add_column("Created")

    for d in sorted(os.listdir(chroma_dir)):
        meta_path = os.path.join(chroma_dir, d, "metadata.json")
        if not os.path.exists(meta_path):
            continue
        with open(meta_path) as f:
            m = json.load(f)
        arch = m.get("architecture", {})
        created = time.strftime("%Y-%m-%d %H:%M", time.localtime(m.get("created_at", 0)))
        table.add_row(
            m.get("project_id", d),
            arch.get("vector_database", "?"),
            str(m.get("chunks_created", "?")),
            created,
        )
    console.print(table)


@app.command("serve")
def serve(
    host: Annotated[str, typer.Option(help="Bind host")] = "0.0.0.0",
    port: Annotated[int, typer.Option(help="Bind port")] = 8000,
    reload: Annotated[bool, typer.Option("--reload", help="Enable hot-reload (dev only)")] = False,
):
    """Start the AutoRAG Architect API server."""
    import uvicorn

    console.print(f"[bold green]Starting AutoRAG Architect on {host}:{port}[/bold green]")
    uvicorn.run("src.main:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()
