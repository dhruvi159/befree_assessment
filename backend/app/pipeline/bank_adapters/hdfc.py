"""HDFC Bank statement adapter."""
import re
import logging
from typing import Optional

from app.pipeline.bank_adapters.base import BankAdapter
from app.pipeline.bank_adapters.generic import GenericAdapter
from app.utils.formatting import parse_date, parse_amount

logger = logging.getLogger(__name__)

HDFC_INDICATORS = ["HDFC BANK", "HDFC Bank Ltd", "HDFCBANK"]


class HDFCAdapter(BankAdapter):
    """
    Adapter for HDFC Bank statements.
    Columns: Date | Narration | Chq./Ref.No. | Value Dt | Withdrawal Amt. | Deposit Amt. | Closing Balance
    Status: tested_on_masked_sample
    """

    bank_name = "HDFC Bank"
    adapter_status = "tested_on_masked_sample"

    def can_parse(self, text: str) -> bool:
        return any(ind.lower() in text.lower() for ind in HDFC_INDICATORS)

    def extract_account_details(self, pages_text: list[str]) -> dict:
        full_text = "\n".join(pages_text[:2])
        generic = GenericAdapter()
        details = generic.extract_account_details(pages_text)
        details["bank_name"] = "HDFC Bank"

        # HDFC-specific patterns
        m = re.search(r"(?i)account\s*number\s*[:\-]?\s*([X\d]{6,20})", full_text)
        if m:
            details["account_number"] = m.group(1).strip()

        return details

    def extract_transactions(self, pages_text: list[tuple[int, str]]) -> list[dict]:
        """Parse HDFC-format transactions with robust amount and balance detection."""
        transactions = []
        date_pattern = re.compile(r"^(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+")
        amount_re = re.compile(r"[\d,]+\.\d{2}")

        running_balance: Optional[float] = None

        for page_num, text in pages_text:
            for raw_line in text.split("\n"):
                line = raw_line.strip()
                if not line or any(h in line.lower() for h in ["narration", "withdrawal amt", "closing balance", "page no"]):
                    continue

                dm = date_pattern.search(line)
                if not dm:
                    continue

                txn_date_str = dm.group(1)
                remainder = line[dm.end():].strip()

                # Clean pipes and OCR column separators
                cleaned_remainder = remainder.replace("|", " ")

                # Find all currency amounts with 2 decimal places (ignore integers / UTR reference numbers)
                amounts_raw = amount_re.findall(cleaned_remainder)
                if not amounts_raw:
                    continue

                amounts = [parse_amount(a) for a in amounts_raw]
                amounts = [a for a in amounts if a is not None]
                if not amounts:
                    continue

                # The last amount on an HDFC statement line is the closing balance
                balance = amounts[-1] if len(amounts) >= 2 else None
                debit = None
                credit = None

                # Description: text preceding the first currency amount
                first_amt_pos = cleaned_remainder.find(amounts_raw[0])
                desc = cleaned_remainder[:first_amt_pos].strip() if first_amt_pos != -1 else cleaned_remainder

                # Detect explicit credit/debit keywords
                upper_line = cleaned_remainder.upper()
                is_credit_kw = any(w in upper_line for w in ["CREDIT", "REFUND", "INTEREST", "SALARY", "DIVIDEND", "DEPOSIT", "CR", "NEFT CR", "IMPS CR", "RTGS CR"])
                is_debit_kw = any(w in upper_line for w in ["DEBIT", "WITHDRAWAL", "DR", "POS ", "ATM ", "PURCHASE", "TAX", "CHARGE", "FEES", "BILLPAY", "SWIGGY", "ZOMATO"])

                if len(amounts) >= 3:
                    # Formats with both Withdrawal and Deposit columns: candidate_debit, candidate_credit, balance
                    c_debit = amounts[-3]
                    c_credit = amounts[-2]
                    if c_debit > 0 and (not c_credit or c_credit == 0):
                        debit = c_debit
                    elif c_credit > 0 and (not c_debit or c_debit == 0):
                        credit = c_credit
                    elif is_credit_kw and not is_debit_kw:
                        credit = c_credit
                    else:
                        debit = c_debit
                elif len(amounts) == 2:
                    # Single transaction amount + Closing balance
                    amt = amounts[0]
                    # Deterministic balance reconciliation if running balance is known
                    if running_balance is not None and balance is not None:
                        expected_diff = round(balance - running_balance, 2)
                        if round(abs(expected_diff) - amt, 2) == 0:
                            if expected_diff < 0:
                                debit = amt
                            else:
                                credit = amt
                        elif is_credit_kw and not is_debit_kw:
                            credit = amt
                        else:
                            debit = amt
                    elif is_credit_kw and not is_debit_kw:
                        credit = amt
                    else:
                        debit = amt

                if balance is not None:
                    running_balance = balance

                transactions.append({
                    "date": parse_date(txn_date_str),
                    "description": desc,
                    "original_description": desc,
                    "debit": debit,
                    "credit": credit,
                    "balance": balance,
                    "source_page": page_num,
                })

        # If HDFC-specific parsing found nothing, fall back to generic
        if not transactions:
            generic = GenericAdapter()
            return generic.extract_transactions(pages_text)

        return transactions

