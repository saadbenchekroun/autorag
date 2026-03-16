import mimetypes
import os
from typing import Any, Dict, List

import markdown  # type: ignore
from bs4 import BeautifulSoup
from docx import Document as DocxDocument
from pypdf import PdfReader

from src.core.config import config


class DocumentIngestionService:
    """Handles raw file reading and textual extraction across multiple formats."""

    def __init__(self) -> None:
        self.supported_extensions: List[str] = config.get_nested(
            "pipeline.ingestion.supported_extensions",
            [".pdf", ".docx", ".txt", ".md", ".html", ".csv", ".json"],
        )

    def ingest_file(self, file_path: str) -> Dict[str, Any]:
        """Reads a file from disk and extracts its raw text and basic metadata."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.supported_extensions:
            raise ValueError(f"Unsupported file type: {ext}")

        raw_text = self._extract_text(file_path, ext)
        stat = os.stat(file_path)

        return {
            "source": file_path,
            "filename": os.path.basename(file_path),
            "type": mimetypes.guess_type(file_path)[0] or "unknown",
            "size_bytes": stat.st_size,
            "raw_text": raw_text,
            "metadata": {"extension": ext},
        }

    def _extract_text(self, file_path: str, ext: str) -> str:
        text = ""
        try:
            if ext == ".pdf":
                reader = PdfReader(file_path)
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
            elif ext == ".docx":
                doc = DocxDocument(file_path)
                text = "\n".join([para.text for para in doc.paragraphs])
            elif ext == ".md":
                with open(file_path, "r", encoding="utf-8") as f:
                    md_text = f.read()
                    html = markdown.markdown(md_text)
                    text = BeautifulSoup(html, "html.parser").get_text()
            elif ext in [".txt", ".csv", ".json", ".html"]:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    if ext == ".html":
                        text = BeautifulSoup(f.read(), "html.parser").get_text()
                    else:
                        text = f.read()
            return text.strip()
        except Exception as e:
            print(f"Error extracting text from {file_path}: {e}")
            return ""


ingestion_service = DocumentIngestionService()
