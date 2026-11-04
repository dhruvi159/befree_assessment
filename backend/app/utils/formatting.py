"""Formatting utilities for INR currency, dates, and amounts."""
import re
from datetime import datetime, date
from typing import Optional


# ── Date Parsing ──────────────────────────────────────────────────────────────

DATE_FORMATS = [
    "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y",
    "%d %b %Y", "%d-%b-%Y", "%d %b %y", "%d-%b-%y",
    "%d/%b/%Y", "%d/%b/%y",
    "%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y",
    "%d %B %Y", "%B %d, %Y",
    "%d%m/%Y", "%d%m-%Y", "%d%m/%y", "%d%m-%y",
]

MONTH_MAP = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "may": "05", "jun": "06", "jul": "07", "aug": "08",
    "sep": "09", "oct": "10", "nov": "11", "dec": "12",
}


def parse_date(date_str: Optional[str]) -> Optional[str]:
    """Parse a date string into YYYY-MM-DD format. Returns None if unparseable."""
    if not date_str:
        return None
    date_str = date_str.strip().strip(".,;:|/\\-")
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return date_str  # already normalized

    # Normalize common OCR digit substitutions (e.g. O1/O2/2026 -> 01/02/2026)
    date_str = re.sub(r"\b[Oo](\d)", r"0\1", date_str)
    date_str = re.sub(r"([/\-\.])[Oo](\d)", r"\g<1>0\2", date_str)

    for fmt in DATE_FORMATS:
        try:
            dt = datetime.strptime(date_str, fmt)
            # Handle 2-digit years: assume 00-29 -> 2000s, 30-99 -> 1900s
            if dt.year < 100:
                dt = dt.replace(year=dt.year + 2000 if dt.year < 30 else dt.year + 1900)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Try manual parsing for formats like "01 Jan 2025"
    m = re.match(r"(\d{1,2})[/\-\s.]([A-Za-z]{3})[/\-\s.](\d{2,4})", date_str)
    if m:
        day, mon, yr = m.group(1), m.group(2).lower(), m.group(3)
        month = MONTH_MAP.get(mon)
        if month:
            if len(yr) == 2:
                yr = "20" + yr if int(yr) < 30 else "19" + yr
            try:
                return f"{int(yr):04d}-{month}-{int(day):02d}"
            except ValueError:
                pass
    return None


def parse_amount(value: Optional[str]) -> Optional[float]:
    """Parse an amount string to float. Handles ₹, commas, Dr/Cr suffixes."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    s = str(value).strip()
    if not s or s in ("-", "—", "N/A", "nil", "NIL"):
        return None

    # Determine sign from Dr/Cr suffix
    sign = 1.0
    s_lower = s.lower()
    if s_lower.endswith("dr") or s_lower.endswith("(dr)"):
        sign = -1.0
        s = re.sub(r"[\s]*(dr|\(dr\))$", "", s, flags=re.IGNORECASE)
    elif s_lower.endswith("cr") or s_lower.endswith("(cr)"):
        sign = 1.0
        s = re.sub(r"[\s]*(cr|\(cr\))$", "", s, flags=re.IGNORECASE)

    # Strip currency symbols and commas
    s = re.sub(r"[₹$€£,\s]", "", s)
    # Handle parentheses as negative
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]
        sign = 1.0

    try:
        return float(s) * sign
    except ValueError:
        return None


def format_inr(amount: Optional[float]) -> str:
    """Format a float as INR with Indian grouping. Returns '' for None."""
    if amount is None:
        return ""
    # Indian number format: 1,23,456.00
    negative = amount < 0
    amount = abs(amount)
    formatted = f"{amount:,.2f}"
    # Convert to Indian grouping: rightmost 3 digits, then groups of 2
    parts = formatted.split(".")
    integer_part = parts[0].replace(",", "")
    if len(integer_part) > 3:
        last3 = integer_part[-3:]
        rest = integer_part[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        integer_part = ",".join(groups) + "," + last3
    result = f"₹{integer_part}.{parts[1]}"
    return f"-{result}" if negative else result

