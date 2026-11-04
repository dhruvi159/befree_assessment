"""Tests for text extractor and bank adapters."""
from pathlib import Path
import pytest
import fitz
from app.pipeline.text_extractor import extract_text_pdf
from app.pipeline.bank_adapters.registry import get_adapter
from app.pipeline.bank_adapters.hdfc import HDFCAdapter
from app.pipeline.bank_adapters.sbi import SBIAdapter


@pytest.fixture
def temp_hdfc_pdf(tmp_path):
    doc = fitz.open()
    page = doc.new_page()
    content = (
        "HDFC BANK LIMITED\n"
        "Customer Name: Test Account Holder\n"
        "Account No: 50100456789123\n"
        "Branch: KORAMANGALA\n"
        "IFSC: HDFC0001234\n"
        "Date        Narration                     Chq/Ref No     Withdrawal   Deposit     Balance\n"
        "01/01/2026  SALARY CR / TECH CORP         REF991001                    85000.00    85000.00\n"
        "02/01/2026  UPI / SWIGGY RESTAURANT       UPI991002       450.00                   84550.00\n"
        "03/01/2026  ATM CASH WDL BANGALORE        ATM991003      2000.00                   82550.00\n"
    )
    page.insert_text((40, 60), content)
    pdf_path = tmp_path / "test_hdfc.pdf"
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


def test_adapter_detection():
    adapter = get_adapter("Welcome to HDFC Bank Ltd Account Statement")
    assert isinstance(adapter, HDFCAdapter)

    adapter_sbi = get_adapter("State Bank of India Account Summary")
    assert isinstance(adapter_sbi, SBIAdapter)


def test_extract_hdfc_text(temp_hdfc_pdf):
    res = extract_text_pdf(temp_hdfc_pdf, [{"page": 1, "type": "text"}])
    assert res["error"] is None
    assert "HDFC" in res["bank_name"]
    assert res["account_details"]["account_holder"] == "Test Account Holder"
    assert len(res["raw_transactions"]) >= 2

    first_txn = res["raw_transactions"][0]
    assert first_txn["date"] is not None
    assert first_txn["balance"] is not None


