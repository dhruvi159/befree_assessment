"""Generic bank statement parser - fallback for unrecognized layouts."""
import re
import logging
from typing import Optional

from app.pipeline.bank_adapters.base import BankAdapter
from app.utils.formatting import parse_date, parse_amount

logger = logging.getLogger(__name__)

# Header patterns that indicate a transaction table
HEADER_PATTERNS = [
    r"(?i)(date|txn\s*date|value\s*date|trans\s*date)",
    r"(?i)(narration|particulars|description|details|remarks)",
    r"(?i)(withdrawal|debit|dr\.?)",
    r"(?i)(deposit|credit|cr\.?)",
    r"(?i)(balance|bal\.?)",
]

# Rows to skip (summary lines, repeated headers, footers, metadata fields)
SKIP_PATTERNS = [
    r"(?i)^\s*(opening|closing)\s*balance",
    r"(?i)^\s*total\s*(debits?|credits?|transactions?)",
    r"(?i)^\s*brought\s*forward",
    r"(?i)^\s*carried\s*forward",
    r"(?i)^\s*page\s*\d+",
    r"(?i)^\s*(date|narration|particulars|description|withdrawal|deposit|balance|txn)",
    r"(?i)^\s*sr\.?\s*no",
    # Account metadata lines — these contain a date-like value but are NOT transactions
    r"(?i)^\s*(nominee|account\s*(type|open|holder|no|number)|mobile|email|ifsc|branch|customer|pan|dob|address|joint\s*holder|product|scheme|mode\s*of\s*operation|cif\s*(no|number)?|nomination)\s*[\:\-]",
    # Lines where amounts are absent AND description looks like a label:value pair
    r"(?i)^\s*[a-z ]{3,40}\s*:\s*[xX\*\d\s]{4,}",
]

DATE_PATTERN = re.compile(
    r"\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d{4}[/\-\.]\d{2,4}|\d{1,2}[\s\-]?[A-Za-z]{3}[\s\-]?\d{2,4})\b"
)

# Match currency amounts: integers or decimals with . or , (e.g. 1,23,456.78 or 74850,00 or 50000)
AMOUNT_PATTERN = re.compile(r"[\d,]+(?:[\.,]\d{2})?")


class GenericAdapter(BankAdapter):
    """
    Generic fallback adapter that uses heuristic column detection.
    Handles both separate debit/credit columns and single Amount+Dr/Cr columns.
    """

    bank_name = "Generic"
    adapter_status = "tested_on_masked_sample"

    def can_parse(self, text: str) -> bool:
        """Generic adapter always returns True as a last-resort fallback."""
        return True

    def extract_account_details(self, pages_text: list[str]) -> dict:
        """Extract account details from statement text using common patterns."""
        full_text = "\n".join(pages_text[:3])  # check first 3 pages
        details = {
            "account_holder": None,
            "bank_name": None,
            "account_number": None,
            "ifsc_code": None,
            "branch": None,
            "statement_period_start": None,
            "statement_period_end": None,
            "opening_balance": None,
            "closing_balance": None,
        }

        # Account holder name
        for pattern in [
            r"(?i)account\s*holder(?:\s*name)?\s*[:\-]?\s*([A-Za-z][A-Za-z \.]{2,50}?)\s*(?:\r?\n|$)",
            r"(?i)customer\s*name\s*[:\-]?\s*([A-Za-z][A-Za-z \.]{2,50}?)\s*(?:\r?\n|$)",
            r"(?i)\bname\s*[:\-]\s*([A-Za-z][A-Za-z \.]{2,50}?)\s*(?:\r?\n|$)",
        ]:
            m = re.search(pattern, full_text)
            if m:
                holder = m.group(1).strip()
                if holder and len(holder) > 2 and not holder.lower().startswith("account"):
                    details["account_holder"] = holder
                    break

        # Account number
        for pattern in [
            r"(?i)account\s*(no|number|num)\.?\s*[:\-]?\s*([X\*\d]{6,20})",
            r"(?i)a/c\s*(no|number)?\s*[:\-]?\s*([X\*\d]{6,20})",
            r"(?i)acc\.?\s*(no|num)\.?\s*[:\-]?\s*([X\*\d]{6,20})",
        ]:
            m = re.search(pattern, full_text)
            if m:
                details["account_number"] = m.group(2).strip()
                break

        # IFSC code
        m = re.search(r"\b([A-Z]{4}0[A-Z0-9]{6})\b", full_text)
        if m:
            details["ifsc_code"] = m.group(1)

        # Branch
        for pattern in [
            r"(?i)branch\s*[:\-]?\s*([A-Za-z0-9 ,]{3,60}?)\s*(?:\r?\n|$)",
            r"(?i)branch\s*name\s*[:\-]?\s*([A-Za-z0-9 ,]{3,60}?)\s*(?:\r?\n|$)",
        ]:
            m = re.search(pattern, full_text)
            if m:
                details["branch"] = m.group(1).strip()
                break

        # Statement period
        period_patterns = [
            r"(?i)statement\s*(period|from|date)\s*[:\-]?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})\s*(?:to|-)?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
            r"(?i)from\s*[:\-]?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})\s*to\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
        ]
        for pattern in period_patterns:
            m = re.search(pattern, full_text)
            if m and len(m.groups()) >= 2:
                dates = [parse_date(m.group(i)) for i in range(len(m.groups()), 0, -1)]
                dates = [d for d in dates if d]
                if len(dates) >= 2:
                    details["statement_period_start"] = min(dates)
                    details["statement_period_end"] = max(dates)
                break

        # Opening balance — various SBI/HDFC/ICICI formats
        for pattern in [
            r"(?i)opening\s*balance\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+\.?\d*)",
            r"(?i)opening\s*bal(?:ance)?\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+\.?\d*)",
            r"(?i)op(?:en(?:ing)?)?\s*bal(?:ance)?\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+\.?\d*)",
            # SBI format: "Balance as on DD-MM-YYYY : 1,234.56"
            r"(?i)balance\s*as\s*on\s*[\d/\-]+\s*[:\-]\s*(?:INR|Rs\.?|₹)?\s*([\d,]+\.?\d*)",
            # Inline table: first numeric value after "Brought Forward"
            r"(?i)brought\s*forward\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+\.?\d{2})",
        ]:
            m = re.search(pattern, full_text)
            if m:
                details["opening_balance"] = parse_amount(m.group(1))
                break

        # Closing balance
        for pattern in [
            r"(?i)closing\s*balance\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+\.?\d*)",
            r"(?i)closing\s*bal(?:ance)?\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+\.?\d*)",
            r"(?i)cl(?:os(?:ing)?)?\s*bal(?:ance)?\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+\.?\d*)",
            r"(?i)carried\s*forward\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+\.?\d{2})",
        ]:
            m = re.search(pattern, full_text)
            if m:
                details["closing_balance"] = parse_amount(m.group(1))
                break

        return details

    def extract_transactions(self, pages_text: list[tuple[int, str]]) -> list[dict]:
        """
        Extract transactions using line-by-line heuristic parsing.
        Handles both split debit/credit and combined Amount+Dr/Cr formats.
        """
        transactions = []

        running_balance: Optional[float] = None

        for page_num, text in pages_text:
            lines = text.split("\n")
            current_txn = None

            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue

                # Skip summary and header lines
                if self._should_skip(stripped):
                    continue

                # Check if this line starts a transaction (has a date in first 30 chars)
                date_match = DATE_PATTERN.search(stripped[:30])
                if date_match:
                    # Save previous transaction
                    if current_txn:
                        transactions.append(current_txn)
                        if current_txn.get("balance") is not None:
                            running_balance = current_txn["balance"]
                    # Parse new transaction
                    current_txn = self._parse_transaction_line(stripped, page_num, running_balance)
                elif current_txn and len(stripped) > 3:
                    # Continuation line (multi-line narration)
                    # Only append if it doesn't look like a pure amount line
                    if not re.match(r"^\s*[\d,]+\.\d{2}\s*$", stripped):
                        current_txn["description"] = (
                            current_txn["description"] + " " + stripped
                        ).strip()

            # Don't forget last transaction on page
            if current_txn:
                transactions.append(current_txn)
                if current_txn.get("balance") is not None:
                    running_balance = current_txn["balance"]

        return transactions

    def _should_skip(self, line: str) -> bool:
        """Return True if this line should be skipped (header, footer, summary)."""
        for pattern in SKIP_PATTERNS:
            if re.match(pattern, line):
                return True
        return False

    def _parse_transaction_line(self, line: str, page_num: int, running_balance: Optional[float] = None) -> dict:
        """Parse a single transaction line into a dict."""
        txn = {
            "date": None,
            "description": "",
            "original_description": line,
            "debit": None,
            "credit": None,
            "balance": None,
            "source_page": page_num,
        }

        # Extract date from beginning of line (allow leading row index / OCR noise)
        date_match = DATE_PATTERN.search(line[:45])
        if date_match:
            txn["date"] = parse_date(date_match.group(0))
            line_after_date = line[date_match.end():].strip()
            # Handle secondary Value Date right after Txn Date (e.g. "04/04/2026 04/04/2026 ...")
            val_date_match = DATE_PATTERN.search(line_after_date[:30])
            if val_date_match and val_date_match.start() <= 3:
                line_after_date = line_after_date[val_date_match.end():].strip()
        else:
            line_after_date = line

        # Detect Dr/Cr markers in the line
        is_debit = bool(re.search(r"(?i)\bdr\.?\b|\bdebit\b|\bwithdraw", line))
        is_credit = bool(re.search(r"(?i)\bcr\.?\b|\bcredit\b|\bdeposit\b|\brefund\b|\bsalary\b", line))

        # Extract amounts from line after date
        amounts_raw = AMOUNT_PATTERN.findall(line_after_date)
        amounts = []
        valid_amounts_raw = []
        for a in amounts_raw:
            clean_digits = a.replace(",", "").replace(".", "")
            # Ignore UTR, cheque, and UPI reference numbers (e.g. 0000103200767201 or 10+ digits without decimals)
            if re.match(r"^0{2,}\d+", a) or (len(clean_digits) >= 9 and "." not in a and not re.search(r",\d{2}$", a)):
                continue

            # Ignore isolated 4-digit calendar years without decimals (e.g. 2024, 2025, 2026)
            if len(clean_digits) == 4 and "." not in a and 2000 <= int(clean_digits) <= 2040:
                continue

            # Handle European OCR decimal comma: e.g. 74850,00 -> 74850.00
            clean_a = a
            if re.search(r",\d{2}$", clean_a) and "." not in clean_a:
                clean_a = re.sub(r",(\d{2})$", r".\1", clean_a)
            parsed = parse_amount(clean_a)
            if parsed is not None and parsed >= 0:
                amounts.append(parsed)
                valid_amounts_raw.append(a)

        # Assign amounts based on count and Dr/Cr context
        # Most Indian bank statements: ... <debit_or_blank> <credit_or_blank> <balance>
        # Blank columns appear as empty strings or are absent — we use Dr/Cr cues
        if len(amounts) >= 3:
            # Three amounts found: treat as Debit | Credit | Balance
            # Exactly one of debit/credit should be non-zero; pick the right one
            candidate_debit = amounts[-3]
            candidate_credit = amounts[-2]
            balance = amounts[-1]

            if candidate_debit > 0 and candidate_credit == 0:
                txn["debit"] = candidate_debit
            elif candidate_credit > 0 and candidate_debit == 0:
                txn["credit"] = candidate_credit
            elif candidate_debit > 0 and candidate_credit > 0:
                # Both non-zero — use Dr/Cr markers to decide, else treat first as debit
                if is_credit and not is_debit:
                    txn["credit"] = candidate_credit
                else:
                    txn["debit"] = candidate_debit
            txn["balance"] = balance

        elif len(amounts) == 2:
            # Two amounts: transaction amount + balance
            txn["balance"] = amounts[-1]
            amt = amounts[0]
            if running_balance is not None and txn["balance"] is not None:
                expected_diff = round(txn["balance"] - running_balance, 2)
                if round(abs(expected_diff) - amt, 2) == 0:
                    if expected_diff < 0:
                        txn["debit"] = amt
                    else:
                        txn["credit"] = amt
                elif is_credit and not is_debit:
                    txn["credit"] = amt
                else:
                    txn["debit"] = amt
            elif is_credit and not is_debit:
                txn["credit"] = amt
            else:
                txn["debit"] = amt

        elif len(amounts) == 1:
            # Only one amount — no balance available
            if is_credit and not is_debit:
                txn["credit"] = amounts[0]
            else:
                txn["debit"] = amounts[0]

        # Description: text between date and the first actual currency amount
        if valid_amounts_raw:
            first_amt_pos = line_after_date.find(valid_amounts_raw[0])
            desc = line_after_date[:first_amt_pos].strip() if first_amt_pos != -1 else line_after_date
        else:
            desc = line_after_date

        # Clean up column separators, dashes, Dr/Cr markers and extra whitespace
        desc = re.sub(r"[\s\-\|]+$", "", desc).strip()
        desc = re.sub(r"(?i)\b(dr|cr|debit|credit)\b", "", desc).strip()
        desc = re.sub(r"\s+", " ", desc).strip()
        txn["description"] = desc

        return txn

