"""Bank adapter registry — auto-detects bank and dispatches to the right adapter."""
import logging
from app.pipeline.bank_adapters.base import BankAdapter
from app.pipeline.bank_adapters.generic import GenericAdapter
from app.pipeline.bank_adapters.hdfc import HDFCAdapter
from app.pipeline.bank_adapters.sbi import SBIAdapter
from app.pipeline.bank_adapters.icici import ICICIAdapter

logger = logging.getLogger(__name__)

# Ordered list: specific adapters first, generic last
ADAPTER_REGISTRY: list[type[BankAdapter]] = [
    HDFCAdapter,
    SBIAdapter,
    ICICIAdapter,
    GenericAdapter,
]


def get_adapter(first_page_text: str) -> BankAdapter:
    """
    Auto-detect the appropriate bank adapter from the first page text.
    Falls back to GenericAdapter if no specific adapter matches.
    """
    for adapter_cls in ADAPTER_REGISTRY[:-1]:  # all except generic
        adapter = adapter_cls()
        if adapter.can_parse(first_page_text):
            logger.info(f"Detected bank adapter: {adapter.bank_name}")
            return adapter

    logger.info("No specific adapter matched. Using GenericAdapter.")
    return GenericAdapter()

