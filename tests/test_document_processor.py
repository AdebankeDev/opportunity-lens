"""
tests/test_document_processor.py — Tests for PDF and text extraction.
"""
import pytest
from document_processor import (
    extract_text_from_pdf,
    validate_pasted_text,
    MAX_DOCUMENT_CHARS,
)


# ── validate_pasted_text ──────────────────────────────────────────────────────

class TestValidatePastedText:
    def test_empty_string_fails(self):
        result = validate_pasted_text("")
        assert not result.success
        assert "No text" in result.error

    def test_whitespace_only_fails(self):
        result = validate_pasted_text("   \n\t  ")
        assert not result.success

    def test_too_short_fails(self):
        result = validate_pasted_text("Short text")
        assert not result.success
        assert "too short" in result.error.lower()

    def test_valid_text_succeeds(self):
        text = "A" * 200
        result = validate_pasted_text(text)
        assert result.success
        assert result.char_count == 200
        assert result.text == text

    def test_long_text_truncated(self):
        text = "B" * (MAX_DOCUMENT_CHARS + 5000)
        result = validate_pasted_text(text)
        assert result.success
        assert result.is_truncated
        assert len(result.text) == MAX_DOCUMENT_CHARS
        assert result.warning is not None

    def test_exactly_at_limit(self):
        text = "C" * MAX_DOCUMENT_CHARS
        result = validate_pasted_text(text)
        assert result.success
        assert not result.is_truncated

    def test_strips_whitespace(self):
        text = "   " + ("D" * 200) + "   "
        result = validate_pasted_text(text)
        assert result.success
        assert not result.text.startswith(" ")
        assert not result.text.endswith(" ")


# ── extract_text_from_pdf ─────────────────────────────────────────────────────

class TestExtractTextFromPdf:
    def test_empty_bytes_fails(self):
        result = extract_text_from_pdf(b"")
        assert not result.success
        assert "empty" in result.error.lower()

    def test_invalid_pdf_bytes_fails(self):
        result = extract_text_from_pdf(b"This is not a PDF at all!")
        assert not result.success

    def test_valid_pdf_succeeds(self):
        """Create a minimal valid PDF in memory using PyMuPDF with extractable text."""
        try:
            import pymupdf as fitz
        except ImportError:
            try:
                import fitz
            except ImportError:
                pytest.skip("PyMuPDF not installed")

        # Use insert_htmlbox which reliably produces selectable text in pymupdf 2.x
        doc = fitz.open()
        page = doc.new_page()
        rect = fitz.Rect(50, 50, 500, 200)
        long_text = (
            "Scholarship Announcement for Test Purposes. "
            "This fellowship is open to postgraduate students from eligible countries. "
            "Minimum CGPA: 3.5 on a 4.0 scale. Deadline: 30 April 2025."
        )
        try:
            page.insert_htmlbox(rect, f"<p>{long_text}</p>")
        except AttributeError:
            # Older pymupdf: use insertTextbox
            page.insertTextbox(rect, long_text, fontsize=11)
        pdf_bytes = doc.tobytes()
        doc.close()

        result = extract_text_from_pdf(pdf_bytes, "test.pdf")
        assert result.success, f"Expected success but got error: {result.error}"
        assert len(result.text) >= 50
        assert result.page_count == 1

    def test_large_file_rejected(self):
        # 21 MB of zeros
        result = extract_text_from_pdf(b"\x00" * (21 * 1024 * 1024))
        assert not result.success
        assert "too large" in result.error.lower()
