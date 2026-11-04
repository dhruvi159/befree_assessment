"""Account number masking utilities for StatementIQ."""
import re
from typing import Optional


def mask_account_number(account_number: Optional[str]) -> Optional[str]:
    """Mask an account number, showing only the last 4 digits."""
    if not account_number:
        return None

    cleaned = re.sub(r"\s+", "", account_number.strip())
    if len(cleaned) <= 4:
        return cleaned

    visible_part = cleaned[-4:]
    masked_part = "*" * (len(cleaned) - 4)
    return masked_part + visible_part


def mask_account_display(account_number: Optional[str]) -> Optional[str]:
    """Return display-formatted masked account number (e.g. •••• •••• 4821)."""
    if not account_number:
        return None
    cleaned = re.sub(r"[\s\-]+", "", account_number.strip())
    if len(cleaned) <= 4:
        return cleaned
    
    hidden_count = len(cleaned) - 4
    num_blocks = (hidden_count + 3) // 4
    blocks = ["••••"] * num_blocks
    blocks.append(cleaned[-4:])
    return " ".join(blocks)


def mask_ifsc(ifsc_code: Optional[str]) -> Optional[str]:
    """Return IFSC code as-is."""
    if not ifsc_code:
        return None
    return ifsc_code.strip().upper()
