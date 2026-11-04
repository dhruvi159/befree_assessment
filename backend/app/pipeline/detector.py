"""PDF page type detection using PyMuPDF (fitz)."""
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import pymupdf as fitz
    PYMUPDF_AVAILABLE = True
except ImportError:
    try:
        import fitz
        PYMUPDF_AVAILABLE = True
    except ImportError:
        PYMUPDF_AVAILABLE = False
        logger.warning("PyMuPDF not available. PDF detection disabled.")

# Minimum chars per page to consider it text-based (not scanned)
TEXT_CHAR_THRESHOLD = 50


def detect_pdf_type(
    pdf_path: str | Path,
    password: Optional[str] = None
) -> dict:
    """
    Detect per-page PDF type (text, scanned) and overall file classification.

    Returns:
        {
            "pdf_type": "text_based" | "scanned" | "mixed",
            "page_count": int,
            "page_types": [{"page": 1, "type": "text", "char_count": 450}, ...],
            "password_protected": bool,
            "error": str | None
        }
    """
    result = {
        "pdf_type": "text_based",
        "page_count": 0,
        "page_types": [],
        "password_protected": False,
        "error": None,
    }

    if not PYMUPDF_AVAILABLE:
        result["error"] = "PyMuPDF not installed"
        return result

    path = Path(pdf_path)
    if not path.exists():
        result["error"] = f"File not found: {pdf_path}"
        return result

    doc = None
    try:
        doc = fitz.open(str(path))

        # Handle password-protected PDFs
        if doc.is_encrypted:
            result["password_protected"] = True
            if not password:
                result["error"] = "PDF is password-protected. Provide password."
                return result
            authenticated = doc.authenticate(password)
            if not authenticated:
                result["error"] = "Incorrect PDF password."
                return result

        result["page_count"] = len(doc)
        text_pages = 0
        scanned_pages = 0

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            char_count = len(text.strip())

            if char_count >= TEXT_CHAR_THRESHOLD:
                page_type = "text"
                text_pages += 1
            else:
                page_type = "scanned"
                scanned_pages += 1

            result["page_types"].append({
                "page": page_num + 1,
                "type": page_type,
                "char_count": char_count,
            })

        # Overall classification
        total = result["page_count"]
        if total == 0:
            result["pdf_type"] = "text_based"
        elif scanned_pages == 0:
            result["pdf_type"] = "text_based"
        elif text_pages == 0:
            result["pdf_type"] = "scanned"
        else:
            result["pdf_type"] = "mixed"

    except fitz.FileDataError as e:
        result["error"] = f"Corrupted or invalid PDF: {e}"
    except Exception as e:
        result["error"] = f"PDF detection error: {e}"
        logger.exception("Error detecting PDF type")
    finally:
        if doc:
            doc.close()

    return result

