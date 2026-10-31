"""
document_processor.py — PDF and text extraction for OpportunityLens.
Uses PyMuPDF (fitz) to extract text from uploaded opportunity announcements.
"""

from __future__ import annotations
import io
from dataclasses import dataclass
from typing import Optional

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

MAX_DOCUMENT_CHARS = 100_000   # ~25 k tokens; generous limit
MAX_FILE_SIZE_MB = 20


@dataclass
class ExtractionResult:
    success: bool
    text: str
    page_count: int = 0
    char_count: int = 0
    error: Optional[str] = None
    warning: Optional[str] = None
    is_scanned: bool = False
    is_truncated: bool = False


def extract_text_from_pdf(file_bytes: bytes, filename: str = "document.pdf") -> ExtractionResult:
    """
    Extract text from a PDF file.

    Returns an ExtractionResult with success=True and the extracted text,
    or success=False with a descriptive error message.
    """
    if not PYMUPDF_AVAILABLE:
        return ExtractionResult(
            success=False,
            text="",
            error="PyMuPDF is not installed. Run: pip install pymupdf",
        )

    # ── Size check ──────────────────────────────────────────────────────────
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        return ExtractionResult(
            success=False,
            text="",
            error=f"File is too large ({size_mb:.1f} MB). Maximum allowed: {MAX_FILE_SIZE_MB} MB.",
        )

    if len(file_bytes) == 0:
        return ExtractionResult(
            success=False,
            text="",
            error="The uploaded file is empty.",
        )

    # ── Open with PyMuPDF ───────────────────────────────────────────────────
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except fitz.FileDataError:
        return ExtractionResult(
            success=False,
            text="",
            error="The file does not appear to be a valid PDF.",
        )
    except Exception as exc:
        return ExtractionResult(
            success=False,
            text="",
            error=f"Could not open the PDF: {exc}",
        )

    # ── Password check ───────────────────────────────────────────────────────
    if doc.needs_pass:
        doc.close()
        return ExtractionResult(
            success=False,
            text="",
            error="The PDF is password-protected. Please provide an unlocked version.",
        )

    page_count = len(doc)
    if page_count == 0:
        doc.close()
        return ExtractionResult(
            success=False,
            text="",
            error="The PDF has no pages.",
        )

    # ── Extract text page by page ────────────────────────────────────────────
    pages_text: list[str] = []
    total_chars = 0

    for page_num in range(page_count):
        try:
            page = doc[page_num]
            text = page.get_text("text")
            pages_text.append(text)
            total_chars += len(text)
        except Exception:
            pages_text.append("")

    doc.close()
    full_text = "\n\n".join(pages_text).strip()

    # ── Scanned-PDF detection ────────────────────────────────────────────────
    if len(full_text) < 50:
        return ExtractionResult(
            success=False,
            text="",
            page_count=page_count,
            is_scanned=True,
            error=(
                "Very little text was extracted from this PDF. "
                "It appears to be a scanned document with no selectable text (image-based PDF). "
                "Please paste the announcement text manually instead."
            ),
        )

    # ── Truncation ───────────────────────────────────────────────────────────
    is_truncated = False
    warning = None
    if len(full_text) > MAX_DOCUMENT_CHARS:
        full_text = full_text[:MAX_DOCUMENT_CHARS]
        is_truncated = True
        warning = (
            f"The document is very long. Only the first {MAX_DOCUMENT_CHARS:,} characters "
            f"were analyzed. If the deadline or key requirements appear near the end, "
            f"paste the relevant sections manually."
        )

    return ExtractionResult(
        success=True,
        text=full_text,
        page_count=page_count,
        char_count=len(full_text),
        is_truncated=is_truncated,
        warning=warning,
    )


def validate_pasted_text(text: str) -> ExtractionResult:
    """
    Validate and clean manually pasted opportunity text.
    """
    text = text.strip()

    if not text:
        return ExtractionResult(
            success=False,
            text="",
            error="No text was provided. Please paste the opportunity announcement.",
        )

    if len(text) < 100:
        return ExtractionResult(
            success=False,
            text="",
            error=(
                "The pasted text is too short to contain a meaningful announcement "
                f"({len(text)} characters). Please paste the full announcement."
            ),
        )

    is_truncated = False
    warning = None
    if len(text) > MAX_DOCUMENT_CHARS:
        text = text[:MAX_DOCUMENT_CHARS]
        is_truncated = True
        warning = f"Text truncated to {MAX_DOCUMENT_CHARS:,} characters for analysis."

    return ExtractionResult(
        success=True,
        text=text,
        char_count=len(text),
        is_truncated=is_truncated,
        warning=warning,
    )

