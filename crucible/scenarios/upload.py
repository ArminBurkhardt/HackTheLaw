"""Upload parsing for playbook scenario generation."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

from pypdf import PdfReader


MAX_UPLOAD_BYTES = 8 * 1024 * 1024


def extract_playbook_text(filename: str, content_type: str | None, data: bytes) -> str:
    if not data:
        raise ValueError("Uploaded file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("Uploaded file is too large. Use a PDF or text file under 8 MB.")

    suffix = Path(filename or "").suffix.lower()
    if suffix == ".pdf" or content_type == "application/pdf":
        return _extract_pdf_text(data)

    if suffix not in {".txt", ".md", ".markdown"} and content_type not in {
        "text/plain",
        "text/markdown",
        "application/octet-stream",
    }:
        raise ValueError("Unsupported playbook file type. Upload a PDF, TXT, or Markdown file.")

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Text playbooks must be UTF-8 encoded.") from exc
    return _clean_text(text)


def _extract_pdf_text(data: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(data))
    except Exception as exc:
        raise ValueError("Could not read the uploaded PDF.") from exc

    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            pages.append(text)
    return _clean_text("\n\n".join(pages))


def _clean_text(text: str) -> str:
    cleaned = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    if len(cleaned) < 600:
        raise ValueError("The uploaded playbook did not contain enough extractable text.")
    return cleaned
