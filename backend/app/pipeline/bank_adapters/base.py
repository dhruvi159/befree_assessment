"""Abstract base class for bank statement adapters."""
from abc import ABC, abstractmethod
from typing import Optional


class BankAdapter(ABC):
    """
    Abstract base for bank-specific statement parsers.
    Each adapter handles extraction for a specific bank's layout.
    """

    bank_name: str = "Unknown"
    adapter_status: str = "untested"  # "tested_on_masked_sample" | "tested_on_real" | "untested"

    @abstractmethod
    def can_parse(self, text: str) -> bool:
        """
        Return True if this adapter recognizes the statement format.
        Called with the full extracted text of the first page.
        """
        pass

    @abstractmethod
    def extract_account_details(self, pages_text: list[str]) -> dict:
        """
        Extract account metadata from statement pages.

        Returns dict with keys:
            account_holder, bank_name, account_number, ifsc_code,
            branch, statement_period_start, statement_period_end,
            opening_balance, closing_balance
        """
        pass

    @abstractmethod
    def extract_transactions(self, pages_text: list[tuple[int, str]]) -> list[dict]:
        """
        Extract transactions from all pages.

        Args:
            pages_text: list of (page_number, text) tuples

        Returns list of dicts with keys:
            date, description, original_description, debit, credit,
            balance, source_page, raw_line (optional)
        """
        pass

