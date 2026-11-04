"""SBI Bank statement adapter."""
import re
from app.pipeline.bank_adapters.base import BankAdapter
from app.pipeline.bank_adapters.generic import GenericAdapter
from app.utils.formatting import parse_date, parse_amount


class SBIAdapter(BankAdapter):
    """
    Adapter for State Bank of India statements.
    Columns: Txn Date | Value Date | Description | Ref No./Cheque No. | Debit | Credit | Balance
    Status: tested_on_masked_sample
    """

    bank_name = "State Bank of India"
    adapter_status = "tested_on_masked_sample"

    def can_parse(self, text: str) -> bool:
        indicators = ["STATE BANK OF INDIA", "SBI", "State Bank of India"]
        return any(ind.lower() in text.lower() for ind in indicators)

    def extract_account_details(self, pages_text: list[str]) -> dict:
        generic = GenericAdapter()
        details = generic.extract_account_details(pages_text)
        details["bank_name"] = "State Bank of India"
        return details

    def extract_transactions(self, pages_text: list[tuple[int, str]]) -> list[dict]:
        transactions = []
        # Support both "01 May 2025" and "04/04/2026" / "04-04-2026" formats
        date_pattern = re.compile(r"^(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d{2}\s+[A-Za-z]{3}\s+\d{4})\s+")
        # Only match proper currency amounts (2 decimal places)
        amount_re = re.compile(r"[\d,]+\.\d{2}")

        running_balance = None

        for page_num, text in pages_text:
            for line in text.split("\n"):
                line = line.strip()
                if not line or "Txn Date" in line:
                    continue
                dm = date_pattern.match(line)
                if not dm:
                    continue

                txn_date_str = dm.group(1)
                remainder = line[dm.end():].strip()

                # Check for optional value date immediately following txn date
                vm = date_pattern.match(remainder)
                if vm:
                    remainder = remainder[vm.end():].strip()

                # Find all currency amounts at the end of line
                amounts_raw = amount_re.findall(remainder)
                if not amounts_raw:
                    continue

                amounts = [parse_amount(a) for a in amounts_raw]
                amounts = [a for a in amounts if a is not None]

                balance = amounts[-1] if amounts else None
                debit = None
                credit = None

                is_cr_kw = any(w in remainder.upper() for w in ["CREDIT", "REFUND", "INTEREST", "SALARY", "DIVIDEND", "NEFT CR", "IMPS CR", "CR "])

                if len(amounts) >= 3:
                    # Debit | Credit | Balance — exactly one of debit/credit is non-zero
                    candidate_debit = amounts[-3]
                    candidate_credit = amounts[-2]
                    if candidate_debit and candidate_debit > 0 and (not candidate_credit or candidate_credit == 0):
                        debit = candidate_debit
                    elif candidate_credit and candidate_credit > 0 and (not candidate_debit or candidate_debit == 0):
                        credit = candidate_credit
                    elif candidate_debit and candidate_credit:
                        if is_cr_kw:
                            credit = candidate_credit
                        else:
                            debit = candidate_debit
                elif len(amounts) == 2:
                    amt = amounts[0]
                    # Deterministic balance difference check
                    if running_balance is not None and balance is not None:
                        expected_diff = round(balance - running_balance, 2)
                        if round(abs(expected_diff) - amt, 2) == 0:
                            if expected_diff < 0:
                                debit = amt
                            else:
                                credit = amt
                        elif is_cr_kw:
                            credit = amt
                        else:
                            debit = amt
                    elif is_cr_kw:
                        credit = amt
                    else:
                        debit = amt
                elif len(amounts) == 1:
                    # Only balance — skip
                    pass

                if balance is not None:
                    running_balance = balance

                # Description is everything before the first amount
                first_amt_pos = remainder.find(amounts_raw[0]) if amounts_raw else -1
                desc = remainder[:first_amt_pos].strip() if first_amt_pos != -1 else remainder

                # Strip trailing dashes or column separators from description
                desc = re.sub(r"[\s\-\|]+$", "", desc).strip()

                transactions.append({
                    "date": parse_date(txn_date_str),
                    "description": desc,
                    "original_description": desc,
                    "debit": debit,
                    "credit": credit,
                    "balance": balance,
                    "source_page": page_num,
                })

        if not transactions:
            generic = GenericAdapter()
            return generic.extract_transactions(pages_text)
        return transactions
