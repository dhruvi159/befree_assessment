"""ICICI Bank statement adapter."""
import re
from app.pipeline.bank_adapters.base import BankAdapter
from app.pipeline.bank_adapters.generic import GenericAdapter
from app.utils.formatting import parse_date, parse_amount


class ICICIAdapter(BankAdapter):
    """
    Adapter for ICICI Bank statements.
    Columns: Transaction Date | Value Date | Particulars | Cheque Number | Debit | Credit | Balance
    Status: tested_on_masked_sample
    """

    bank_name = "ICICI Bank"
    adapter_status = "tested_on_masked_sample"

    def can_parse(self, text: str) -> bool:
        indicators = ["ICICI BANK", "ICICI Bank", "icicibank"]
        return any(ind.lower() in text.lower() for ind in indicators)

    def extract_account_details(self, pages_text: list[str]) -> dict:
        generic = GenericAdapter()
        details = generic.extract_account_details(pages_text)
        details["bank_name"] = "ICICI Bank"
        return details

    def extract_transactions(self, pages_text: list[tuple[int, str]]) -> list[dict]:
        transactions = []
        # ICICI uses dd/mm/yyyy format
        txn_pattern = re.compile(
            r"(\d{2}/\d{2}/\d{4})\s+"  # Transaction date
            r"(\d{2}/\d{2}/\d{4})?\s*" # Value date (optional)
            r"(.+?)\s+"                 # Particulars
            r"(\d*)?\s*"               # Cheque number (optional)
            r"([\d,]*\.?\d*)\s+"       # Debit
            r"([\d,]*\.?\d*)\s+"       # Credit
            r"([\d,]+\.?\d*)"          # Balance
        )

        for page_num, text in pages_text:
            for line in text.split("\n"):
                line = line.strip()
                if not line:
                    continue
                m = txn_pattern.match(line)
                if m:
                    debit = parse_amount(m.group(5))
                    credit = parse_amount(m.group(6))
                    transactions.append({
                        "date": parse_date(m.group(1)),
                        "description": m.group(3).strip(),
                        "original_description": m.group(3).strip(),
                        "debit": debit if debit and debit > 0 else None,
                        "credit": credit if credit and credit > 0 else None,
                        "balance": parse_amount(m.group(7)),
                        "source_page": page_num,
                    })

        if not transactions:
            generic = GenericAdapter()
            return generic.extract_transactions(pages_text)
        return transactions

