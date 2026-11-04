"""Tests for PDF detection engine."""
from pathlib import Path
import pytest
import fitz
from app.pipeline.detector import detect_pdf_type


@pytest.fixture
def temp_text_pdf(tmp_path):
    doc = fitz.open()
    page = doc.new_page()
    text = (
        "HDFC BANK STATEMENT\n"
        "Customer Name: User Account\n"
        "Account No: 50100234567890\n"
        "Date        Narration         Chq/Ref No     Withdrawal   Deposit     Balance\n"
        "01/01/2026  SALARY CREDIT     REF12345                     75000.00    75000.00\n"
        "02/01/2026  SWIGGY FOOD ORDER REF12346       450.00                   74550.00\n"
    )
    page.insert_text((50, 72), text)
    pdf_path = tmp_path / "test_statement.pdf"
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def temp_scanned_pdf(tmp_path):
    doc = fitz.open()
    # Empty page with 0 extractable characters represents scanned page
    doc.new_page()
    pdf_path = tmp_path / "test_scanned.pdf"
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


def test_detect_text_based(temp_text_pdf):
    res = detect_pdf_type(temp_text_pdf)
    assert res["error"] is None
    assert res["page_count"] >= 1
    assert res["pdf_type"] == "text_based"
    assert res["page_types"][0]["type"] == "text"
    assert res["password_protected"] is False


def test_detect_scanned(temp_scanned_pdf):
    res = detect_pdf_type(temp_scanned_pdf)
    assert res["error"] is None
    assert res["pdf_type"] in ["scanned", "mixed"]


def test_detect_missing_file(tmp_path):
    res = detect_pdf_type(tmp_path / "non_existent.pdf")
    assert res["error"] is not None


