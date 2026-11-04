"""Narration preprocessing for classification."""
import re
import unicodedata


# Noise tokens to remove (payment method prefixes - not categories)
PAYMENT_METHOD_PREFIXES = [
    r"\bUPI/",
    r"\bIMPS/",
    r"\bNEFT/",
    r"\bRTGS/",
    r"\bNACH[/-]",
    r"\bACH[/-]",
    r"\bATM/",
    r"\bPOS/",
    r"\bCDM/",
]

# UPI handle pattern (@xxxx)
UPI_HANDLE_PATTERN = re.compile(r"@[\w.]+")

# Reference number patterns (long digit strings, alphanumeric refs)
REF_NUMBER_PATTERN = re.compile(r"\b\d{6,}\b")
ALPHANUM_REF_PATTERN = re.compile(r"\b[A-Z0-9]{10,}\b")

# Common noise words
NOISE_WORDS = {
    "payment", "pay", "paid", "transfer", "txn", "transaction",
    "ref", "reference", "no", "num", "id", "via", "to", "from",
    "dt", "date", "mob", "mobile", "cr", "dr",
}


def normalize_narration(text: str) -> str:
    """
    Normalize a transaction narration for classification.
    - Lowercase
    - Remove payment method prefixes (UPI/, NEFT/, etc.)
    - Remove UPI handles (@xxx)
    - Remove long reference numbers
    - Strip noise tokens
    """
    if not text:
        return ""

    # Normalize unicode
    text = unicodedata.normalize("NFKD", text)
    text = text.lower()

    # Remove payment method prefixes
    for prefix in PAYMENT_METHOD_PREFIXES:
        text = re.sub(prefix, " ", text, flags=re.IGNORECASE)

    # Remove UPI handles
    text = UPI_HANDLE_PATTERN.sub(" ", text)

    # Remove reference numbers (8+ digit strings)
    text = REF_NUMBER_PATTERN.sub(" ", text)

    # Remove long alphanumeric reference codes
    text = ALPHANUM_REF_PATTERN.sub(" ", text)

    # Remove special characters (keep letters, digits, spaces, hyphens)
    text = re.sub(r"[^a-z0-9\s\-]", " ", text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def extract_merchant(narration: str) -> str:
    """
    Extract the likely merchant/counterparty name from a narration.
    Returns normalized merchant name or empty string.
    """
    if not narration:
        return ""

    normalized = normalize_narration(narration)

    # For UPI transactions, merchant is usually first meaningful word after UPI/
    # e.g. "UPI/SWIGGY/..." -> "swiggy"
    upi_match = re.search(r"(?:upi\s*/?\s*)([a-z][a-z0-9\s]{1,30}?)(?:\s*[/|]|$)", narration.lower())
    if upi_match:
        merchant = upi_match.group(1).strip()
        if merchant and merchant not in NOISE_WORDS:
            return merchant

    # First significant token (not a noise word)
    tokens = normalized.split()
    for token in tokens:
        if len(token) > 2 and token not in NOISE_WORDS and not token.isdigit():
            return token

    return normalized[:30]

