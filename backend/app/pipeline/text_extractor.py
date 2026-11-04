"""Text-based PDF extraction using pdfplumber."""
import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    logger.warning("pdfplumber not available.")

from app.pipeline.bank_adapters.registry import get_adapter


def extract_text_pdf(
    pdf_path: str | Path,
    page_types: list[dict],
    password: Optional[str] = None,
) -> dict:
    """
    Extract text from a PDF using pdfplumber for text-based pages.
    Returns account details + raw transactions list.

    Args:
        pdf_path: Path to the PDF file.
        page_types: list of {page, type} from detector.
        password: Optional PDF password.

    Returns:
        {
            "account_details": dict,
            "raw_transactions": list[dict],
            "bank_name": str,
            "pages_text": list[str],
            "error": str | None,
        }
    """
    result = {
        "account_details": {},
        "raw_transactions": [],
        "bank_name": "Unknown",
        "pages_text": [],
        "error": None,
    }

    if not PDFPLUMBER_AVAILABLE:
        result["error"] = "pdfplumber not installed"
        return result

    path = Path(pdf_path)

    try:
        open_kwargs = {"password": password} if password else {}
        with pdfplumber.open(str(path), **open_kwargs) as pdf:
            pages_text = []
            pages_tuples = []  # (page_num, text)

            # Determine which pages are text-based
            text_page_nums = {
                p["page"] for p in page_types if p["type"] == "text"
            }
            # If no page_types provided, treat all as text
            if not page_types:
                text_page_nums = set(range(1, len(pdf.pages) + 1))

            for i, page in enumerate(pdf.pages):
                page_num = i + 1
                if page_num not in text_page_nums:
                    continue  # Will be handled by OCR

                # Extract full text including headers, account metadata, and transaction rows
                text = page.extract_text(layout=True) or page.extract_text() or ""
                
                # If there are structured tables, append them if text was sparse
                tables = page.extract_tables()
                if tables and len(text.strip()) < 50:
                    table_text = ""
                    for table in tables:
                        for row in table:
                            if row:
                                clean_row = [
                                    str(cell).strip() if cell else ""
                                    for cell in row
                                ]
                                table_text += "\t".join(clean_row) + "\n"
                    if len(table_text) > len(text):
                        text = table_text

                pages_text.append(text)
                pages_tuples.append((page_num, text))

            result["pages_text"] = pages_text

            if not pages_text:
                result["error"] = "No text pages found to extract"
                return result

            # Detect bank and get adapter
            first_page_text = pages_text[0] if pages_text else ""
            adapter = get_adapter(first_page_text)
            result["bank_name"] = adapter.bank_name

            # Extract account details
            result["account_details"] = adapter.extract_account_details(pages_text)
            if not result["account_details"].get("bank_name"):
                result["account_details"]["bank_name"] = adapter.bank_name

            # Extract transactions
            result["raw_transactions"] = adapter.extract_transactions(pages_tuples)

    except Exception as e:
        result["error"] = f"Text extraction error: {e}"
        logger.exception("Error during text extraction")

    return result

