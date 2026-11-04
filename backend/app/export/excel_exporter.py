"""Excel exporter using openpyxl."""
import io
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import openpyxl
    from openpyxl.styles import (
        Font, PatternFill, Alignment, Border, Side, numbers
    )
    from openpyxl.utils import get_column_letter
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False
    logger.warning("openpyxl not available.")

# Colors
HEADER_BG = "4444DB"
HEADER_FG = "FFFFFF"
ALT_ROW_BG = "F6F7FB"
FLAGGED_BG = "FFF9EB"


def export_excel(statement, transactions: list, validation_summary: Optional[dict] = None) -> bytes:
    """
    Generate a multi-sheet Excel workbook.

    Sheets:
    1. Transactions - all transactions
    2. Account Summary - account details
    3. Category Summary - spend by category
    4. Validation Report - flagged rows

    Returns bytes of the .xlsx file.
    """
    if not OPENPYXL_AVAILABLE:
        raise RuntimeError("openpyxl not installed")

    wb = openpyxl.Workbook()

    # ── Sheet 1: Transactions ────────────────────────────────────
    ws_txn = wb.active
    ws_txn.title = "Transactions"
    _build_transactions_sheet(ws_txn, transactions)

    # ── Sheet 2: Account Summary ─────────────────────────────────
    ws_acct = wb.create_sheet("Account Summary")
    _build_account_summary_sheet(ws_acct, statement, transactions)

    # ── Sheet 3: Category Summary ────────────────────────────────
    ws_cat = wb.create_sheet("Category Summary")
    _build_category_summary_sheet(ws_cat, transactions)

    # ── Sheet 4: Validation Report ───────────────────────────────
    ws_val = wb.create_sheet("Validation Report")
    _build_validation_sheet(ws_val, transactions, validation_summary)

    # Save to bytes
    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()


def _header_style():
    return {
        "font": Font(bold=True, color=HEADER_FG, size=9),
        "fill": PatternFill("solid", fgColor=HEADER_BG),
        "alignment": Alignment(horizontal="center", vertical="center"),
    }


def _apply_header(ws, headers: list[str], row: int = 1):
    """Apply formatted headers to a worksheet row."""
    style = _header_style()
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=row, column=col, value=header)
        cell.font = style["font"]
        cell.fill = style["fill"]
        cell.alignment = style["alignment"]
    ws.row_dimensions[row].height = 20


def _fmt_amount(val) -> Optional[float]:
    return round(float(val), 2) if val is not None else None


def _build_transactions_sheet(ws, transactions: list):
    headers = [
        "Date", "Description", "Original Description",
        "Debit (₹)", "Credit (₹)", "Balance (₹)",
        "Category", "Method", "Confidence", "Review Status",
        "Validation Flags", "Source Page"
    ]
    _apply_header(ws, headers)

    from app.utils.masking import mask_account_display

    for i, txn in enumerate(transactions, 2):
        flags = txn.get("validation_flags") or []
        is_flagged = bool(flags)
        fill = PatternFill("solid", fgColor=FLAGGED_BG) if is_flagged else None
        conf = txn.get("confidence")

        row_data = [
            txn.get("date", ""),
            txn.get("description", ""),
            txn.get("original_description", ""),
            _fmt_amount(txn.get("debit")),
            _fmt_amount(txn.get("credit")),
            _fmt_amount(txn.get("balance")),
            txn.get("category", ""),
            txn.get("classification_method", ""),
            round(conf * 100, 1) if conf is not None else None,
            txn.get("review_status", ""),
            ", ".join(flags),
            txn.get("source_page", ""),
        ]
        for col, val in enumerate(row_data, 1):
            cell = ws.cell(row=i, column=col, value=val)
            cell.font = Font(size=8)
            if fill:
                cell.fill = fill
            if col in (4, 5, 6):  # amount columns
                cell.number_format = '#,##0.00'
                cell.alignment = Alignment(horizontal="right")

    # Freeze header row
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    # Adjust column widths
    col_widths = [12, 40, 40, 14, 14, 14, 20, 16, 12, 14, 30, 10]
    for col, width in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(col)].width = width


def _build_account_summary_sheet(ws, statement, transactions: list):
    from app.utils.masking import mask_account_display

    ws.column_dimensions["A"].width = 25
    ws.column_dimensions["B"].width = 35

    _apply_header(ws, ["Field", "Value"])

    masked_acct = mask_account_display(getattr(statement, "account_number", None))
    total_debits = sum(t.get("debit") or 0 for t in transactions)
    total_credits = sum(t.get("credit") or 0 for t in transactions)

    rows = [
        ("Account Holder", getattr(statement, "account_holder", "")),
        ("Bank Name", getattr(statement, "bank_name", "")),
        ("Account Number", masked_acct or ""),
        ("IFSC Code", getattr(statement, "ifsc_code", "")),
        ("Branch", getattr(statement, "branch", "")),
        ("Statement Period Start", getattr(statement, "statement_period_start", "")),
        ("Statement Period End", getattr(statement, "statement_period_end", "")),
        ("Opening Balance (₹)", getattr(statement, "opening_balance", None)),
        ("Closing Balance (₹)", getattr(statement, "closing_balance", None)),
        ("Total Transactions", len(transactions)),
        ("Total Debits (₹)", round(total_debits, 2)),
        ("Total Credits (₹)", round(total_credits, 2)),
        ("Net Change (₹)", round(total_credits - total_debits, 2)),
        ("PDF Type", getattr(statement, "pdf_type", "")),
        ("Processed At", str(getattr(statement, "completed_at", ""))),
        ("", ""),
        ("NOTE", "Account number masked for privacy. Last 4 digits shown only."),
    ]

    for i, (field, value) in enumerate(rows, 2):
        ws.cell(row=i, column=1, value=field).font = Font(bold=True, size=9)
        cell = ws.cell(row=i, column=2, value=value)
        cell.font = Font(size=9)
        if isinstance(value, float) and field not in ("Net Change (₹)",):
            cell.number_format = '#,##0.00'


def _build_category_summary_sheet(ws, transactions: list):
    _apply_header(ws, ["Category", "Transaction Count", "Total Debit (₹)", "Total Credit (₹)", "Net (₹)"])

    # Aggregate by category
    cat_data: dict[str, dict] = {}
    for txn in transactions:
        cat = txn.get("category", "Uncategorized")
        if cat not in cat_data:
            cat_data[cat] = {"count": 0, "debit": 0.0, "credit": 0.0}
        cat_data[cat]["count"] += 1
        cat_data[cat]["debit"] += txn.get("debit") or 0
        cat_data[cat]["credit"] += txn.get("credit") or 0

    # Sort by total amount descending
    sorted_cats = sorted(cat_data.items(), key=lambda x: x[1]["debit"] + x[1]["credit"], reverse=True)

    for i, (cat, data) in enumerate(sorted_cats, 2):
        net = data["credit"] - data["debit"]
        row = [cat, data["count"], round(data["debit"], 2), round(data["credit"], 2), round(net, 2)]
        for col, val in enumerate(row, 1):
            cell = ws.cell(row=i, column=col, value=val)
            cell.font = Font(size=9)
            if col >= 3:
                cell.number_format = '#,##0.00'
                cell.alignment = Alignment(horizontal="right")
        if i % 2 == 0:
            for col in range(1, 6):
                ws.cell(row=i, column=col).fill = PatternFill("solid", fgColor=ALT_ROW_BG)

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for col, width in [(1, 25), (2, 18), (3, 18), (4, 18), (5, 18)]:
        ws.column_dimensions[get_column_letter(col)].width = width


def _build_validation_sheet(ws, transactions: list, summary: Optional[dict]):
    _apply_header(ws, ["Date", "Description", "Debit", "Credit", "Balance", "Flags", "Review Status"])

    flagged = [t for t in transactions if t.get("validation_flags")]
    for i, txn in enumerate(flagged, 2):
        flags = ", ".join(txn.get("validation_flags") or [])
        row = [
            txn.get("date", ""), txn.get("description", ""),
            _fmt_amount(txn.get("debit")), _fmt_amount(txn.get("credit")),
            _fmt_amount(txn.get("balance")), flags, txn.get("review_status", ""),
        ]
        for col, val in enumerate(row, 1):
            cell = ws.cell(row=i, column=col, value=val)
            cell.font = Font(size=8)
            cell.fill = PatternFill("solid", fgColor=FLAGGED_BG)
            if col in (3, 4, 5):
                cell.number_format = '#,##0.00'

    if summary:
        summary_row = len(flagged) + 4
        ws.cell(row=summary_row, column=1, value="Summary").font = Font(bold=True)
        ws.cell(row=summary_row + 1, column=1, value="Total flagged:")
        ws.cell(row=summary_row + 1, column=2, value=summary.get("flagged_count", 0))
        ws.cell(row=summary_row + 2, column=1, value="Balance reconciled:")
        ws.cell(row=summary_row + 2, column=2, value="Yes" if summary.get("balance_reconciled") else "No")

    ws.freeze_panes = "A2"
    for col, width in [(1, 12), (2, 40), (3, 14), (4, 14), (5, 14), (6, 40), (7, 16)]:
        ws.column_dimensions[get_column_letter(col)].width = width

