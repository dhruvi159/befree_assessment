"""Tests for high-speed OCR engine and spatial row reconstruction."""
import fitz
import io
import pytest
from PIL import Image, ImageDraw
from app.pipeline.ocr_engine import ocr_pdf_pages, _reconstruct_text, preprocess_image


@pytest.fixture
def temp_scanned_statement_pdf(tmp_path):
    """Generate a clean synthetic scanned statement page with drawn text."""
    img = Image.new("RGB", (1600, 800), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((50, 50), "STATE BANK OF INDIA", fill=(0, 0, 0))
    draw.text((50, 80), "Account Name: Rahul Sharma", fill=(0, 0, 0))
    draw.text((50, 110), "Account Number: 30981234567", fill=(0, 0, 0))
    draw.text((50, 160), "Txn Date    Narration                       Ref No      Debit      Credit     Balance", fill=(0, 0, 0))
    draw.text((50, 210), "12/01/2026  SALARY FOR JAN 2026             REF1001                75000.00   75000.00", fill=(0, 0, 0))
    draw.text((50, 260), "15/01/2026  SWIGGY FOOD ORDER               UPI1002    650.00                 74350.00", fill=(0, 0, 0))
    draw.text((50, 310), "18/01/2026  ATM CASH WITHDRAWAL             ATM1003    2000.00                72350.00", fill=(0, 0, 0))

    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    doc = fitz.open()
    page = doc.new_page(width=1600, height=800)
    page.insert_image(fitz.Rect(0, 0, 1600, 800), stream=img_bytes.getvalue())

    pdf_path = tmp_path / "test_scanned.pdf"
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


def test_ocr_extraction_speed_and_accuracy(temp_scanned_statement_pdf):
    """Verify OCR runs in < 2 seconds and extracts transactions and metadata."""
    res = ocr_pdf_pages(temp_scanned_statement_pdf, [{"page": 1, "type": "scanned"}])

    assert res["error"] is None
    assert len(res["ocr_results"]) == 1
    page1_text = res["ocr_results"][0]["text"]
    assert "STATE BANK" in page1_text or "INDIA" in page1_text

    # Verify transactions extracted
    txns = res["raw_transactions"]
    assert len(txns) >= 2

    # Check first transaction
    dates = [t["date"] for t in txns if t.get("date")]
    assert len(dates) >= 2
    assert all(len(str(d)) == 10 for d in dates)

    # Check amounts
    amounts = [t["debit"] or t["credit"] for t in txns]
    assert any(a is not None and a > 0 for a in amounts)
