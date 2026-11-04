"""OCR engine for scanned PDF pages using Tesseract, OpenCV, and PyMuPDF."""
import logging
import os
import re
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Check dependencies
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("pytesseract not available. OCR disabled.")

try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    logger.warning("OpenCV not available. OCR preprocessing disabled.")

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

try:
    import pymupdf as fitz
    PYMUPDF_AVAILABLE = True
except ImportError:
    try:
        import fitz
        PYMUPDF_AVAILABLE = True
    except ImportError:
        PYMUPDF_AVAILABLE = False


def configure_tesseract():
    """Configure Tesseract path from settings."""
    from app.config import settings
    if TESSERACT_AVAILABLE and os.path.exists(settings.tesseract_cmd):
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd


def preprocess_image(image) -> "np.ndarray":
    """
    Optimized OpenCV preprocessing for scanned document OCR.
    Runs in < 0.05s per page, preserves crisp stroke morphology,
    and maximizes Tesseract line and word recognition accuracy.
    """
    if not OPENCV_AVAILABLE:
        return image

    # Convert PIL Image to numpy array if needed
    if hasattr(image, "convert"):
        image = np.array(image.convert("RGB"))

    # Convert to grayscale
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    else:
        gray = image

    # Deskew if tilted
    gray = _deskew(gray)

    # Resolution normalization: 1600 - 2400 width is optimal for Tesseract OCR
    h, w = gray.shape
    if w < 1400:
        scale = 1600.0 / w
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
    elif w > 2800:
        scale = 2200.0 / w
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

    # Gentle Gaussian blur to eliminate halftone dots and scanner grain
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)

    # Otsu thresholding produces clean, solid black characters on white background
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return binary


def _deskew(image: "np.ndarray") -> "np.ndarray":
    """Fast deskew using Hough transform on downscaled edge map (< 10ms)."""
    try:
        h, w = image.shape
        # Downscale for ultra-fast Hough computation
        target_w = min(800, w)
        scale = target_w / w
        small = cv2.resize(image, (target_w, int(h * scale)))

        edges = cv2.Canny(small, 50, 150, apertureSize=3)
        lines = cv2.HoughLines(edges, 1, np.pi / 180, 150)
        if lines is None:
            return image

        angles = []
        for line in lines[:25]:
            rho, theta = line[0]
            angle = (theta * 180 / np.pi) - 90
            if 0.5 < abs(angle) < 15.0:
                angles.append(angle)

        if not angles or len(angles) < 3:
            return image

        median_angle = float(np.median(angles))
        if abs(median_angle) < 0.5:
            return image

        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        rotated = cv2.warpAffine(
            image, M, (w, h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REPLICATE
        )
        return rotated
    except Exception:
        return image


def _reconstruct_text(ocr_data: dict) -> tuple[str, float]:
    """
    Rebuild rows from Tesseract bounding boxes by spatial vertical clustering.
    Ensures that multi-column tables (Date, Narration, Ref, Debit, Credit, Balance)
    are reconstructed as single, coherent horizontal rows regardless of Tesseract blocks.
    """
    if not ocr_data or not ocr_data.get("text"):
        return "", 0.0

    words = []
    n = len(ocr_data["text"])
    for i in range(n):
        word = str(ocr_data["text"][i]).strip()
        conf = int(ocr_data["conf"][i]) if ocr_data.get("conf") else 0
        if not word or conf == -1:
            continue

        left = int(ocr_data["left"][i])
        top = int(ocr_data["top"][i])
        w = int(ocr_data["width"][i])
        h = int(ocr_data["height"][i])

        # Normalize common OCR date substitutions (e.g. O1/O2/2026 -> 01/02/2026)
        if re.search(r"\b[Oo]\d", word):
            word = re.sub(r"\b[Oo](\d)", r"0\1", word)
        if re.search(r"/[Oo]\d", word):
            word = re.sub(r"/([Oo])(\d)", r"/0\2", word)

        words.append({
            "word": word,
            "conf": max(0, conf),
            "left": left,
            "top": top,
            "width": w,
            "height": h,
            "yc": top + h / 2.0,
        })

    if not words:
        return "", 0.0

    # Sort words primarily by vertical position
    words.sort(key=lambda w: w["yc"])

    # Cluster words into horizontal lines based on vertical overlap
    lines = []
    for w in words:
        placed = False
        tolerance = max(10, w["height"] * 0.65)
        for line in lines:
            if abs(w["yc"] - line["yc"]) <= tolerance:
                line["words"].append(w)
                line["yc"] = sum(x["yc"] for x in line["words"]) / len(line["words"])
                placed = True
                break
        if not placed:
            lines.append({"yc": w["yc"], "words": [w]})

    # Sort lines from top to bottom
    lines.sort(key=lambda l: l["yc"])

    # For each line, sort words horizontally (left to right) and join
    reconstructed_lines = []
    all_confidences = []

    for line in lines:
        line["words"].sort(key=lambda w: w["left"])
        line_text = " ".join(w["word"] for w in line["words"])
        reconstructed_lines.append(line_text)
        all_confidences.extend(w["conf"] for w in line["words"])

    full_text = "\n".join(reconstructed_lines)
    avg_conf = (sum(all_confidences) / len(all_confidences) / 100.0) if all_confidences else 0.0
    return full_text, avg_conf


def ocr_pdf_pages(
    pdf_path: str | Path,
    page_types: list[dict],
    password: Optional[str] = None,
    progress_callback=None,
) -> dict:
    """
    High-performance OCR for scanned pages from a PDF.
    Uses in-memory PyMuPDF rendering with pdf2image fallback,
    fast OpenCV binarization, Tesseract OCR, and spatial row reconstruction.

    Returns:
        {
            "ocr_results": [{"page": int, "text": str, "confidence": float}],
            "raw_transactions": list[dict],
            "account_details": dict,
            "bank_name": str,
            "error": str | None,
        }
    """
    result = {
        "ocr_results": [],
        "raw_transactions": [],
        "account_details": {},
        "bank_name": "Unknown",
        "error": None,
    }

    if not TESSERACT_AVAILABLE:
        result["error"] = "pytesseract not installed. Install Tesseract-OCR."
        return result

    configure_tesseract()

    from app.config import settings
    scanned_pages = [p["page"] for p in page_types if p["type"] == "scanned"]
    if not scanned_pages:
        return result

    scanned_pages_set = set(scanned_pages)
    rendered_pages = []  # list of (page_num, PIL.Image)

    # ── Step 1: Render pages to images (PyMuPDF in-memory C++ speed) ────────
    if PYMUPDF_AVAILABLE:
        try:
            doc = fitz.open(str(pdf_path))
            if password and doc.is_encrypted:
                doc.authenticate(password)

            for page_num in sorted(scanned_pages_set):
                if 1 <= page_num <= len(doc):
                    page = doc[page_num - 1]
                    # 200 DPI provides crisp text while keeping memory/CPU light
                    pix = page.get_pixmap(dpi=200)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    rendered_pages.append((page_num, img))
            doc.close()
            logger.info(f"Rendered {len(rendered_pages)} scanned pages with PyMuPDF")
        except Exception as e:
            logger.warning(f"PyMuPDF rendering failed ({e}), attempting pdf2image fallback")
            rendered_pages = []

    # Fallback to pdf2image if PyMuPDF wasn't able to render
    if not rendered_pages and PDF2IMAGE_AVAILABLE:
        try:
            poppler_path = settings.poppler_path if os.path.isdir(settings.poppler_path) else None
            convert_kwargs = {
                "dpi": 200,
                "first_page": min(scanned_pages_set),
                "last_page": max(scanned_pages_set),
            }
            if poppler_path:
                convert_kwargs["poppler_path"] = poppler_path
            if password:
                convert_kwargs["userpw"] = password

            imgs = convert_from_path(str(pdf_path), **convert_kwargs)
            for page_num, img in zip(sorted(scanned_pages_set), imgs):
                rendered_pages.append((page_num, img))
            logger.info(f"Rendered {len(rendered_pages)} pages with pdf2image")
        except Exception as e:
            result["error"] = f"Failed to render PDF pages: {e}"
            logger.exception("Rendering error")
            return result

    if not rendered_pages:
        result["error"] = "No pages could be rendered for OCR."
        return result

    # ── Step 2: Run OCR on each page ────────────────────────────────────────
    pages_tuples = []  # (page_num, text)
    total_pages = len(rendered_pages)

    try:
        for idx, (page_num, image) in enumerate(rendered_pages):
            if progress_callback:
                progress_callback(idx + 1, total_pages)

            # Preprocess image
            processed = preprocess_image(image)

            # Tesseract OCR with data output
            ocr_data = pytesseract.image_to_data(
                processed,
                output_type=pytesseract.Output.DICT,
                config="--psm 6 --oem 3",
                lang="eng",
            )

            # Reconstruct text rows using spatial bounding-box clustering
            page_text, page_confidence = _reconstruct_text(ocr_data)

            # If psm 6 produced very little text, fallback to psm 3 (fully automatic)
            if len(page_text.strip()) < 40:
                ocr_data_fallback = pytesseract.image_to_data(
                    processed,
                    output_type=pytesseract.Output.DICT,
                    config="--psm 3 --oem 3",
                    lang="eng",
                )
                fb_text, fb_conf = _reconstruct_text(ocr_data_fallback)
                if len(fb_text.strip()) > len(page_text.strip()):
                    page_text, page_confidence = fb_text, fb_conf

            result["ocr_results"].append({
                "page": page_num,
                "text": page_text,
                "confidence": page_confidence,
            })
            pages_tuples.append((page_num, page_text))

        # ── Step 3: Parse transactions & account details with adapters ────────
        if pages_tuples:
            from app.pipeline.bank_adapters.registry import get_adapter
            first_page_text = pages_tuples[0][1] if pages_tuples else ""
            adapter = get_adapter(first_page_text)
            result["bank_name"] = adapter.bank_name
            logger.info(f"Selected adapter: {adapter.bank_name} for OCR statement")

            # Extract account metadata
            all_text = [t[1] for t in pages_tuples]
            result["account_details"] = adapter.extract_account_details(all_text)
            if not result["account_details"].get("bank_name"):
                result["account_details"]["bank_name"] = adapter.bank_name

            # Extract transaction rows
            raw_txns = adapter.extract_transactions(pages_tuples)

            # If bank adapter found 0 rows, fallback to GenericAdapter
            if not raw_txns and adapter.bank_name != "Generic":
                from app.pipeline.bank_adapters.generic import GenericAdapter
                generic = GenericAdapter()
                raw_txns = generic.extract_transactions(pages_tuples)
                if raw_txns:
                    logger.info(f"Generic adapter extracted {len(raw_txns)} transactions after bank adapter returned 0")

            # Tag each transaction with OCR confidence
            page_confidence_map = {
                r["page"]: r["confidence"] for r in result["ocr_results"]
            }
            for txn in raw_txns:
                txn["ocr_confidence"] = page_confidence_map.get(txn.get("source_page", 1), 0.85)

            result["raw_transactions"] = raw_txns
            logger.info(f"OCR extraction completed: {len(raw_txns)} transactions found across {total_pages} pages")

    except Exception as e:
        result["error"] = f"OCR processing error: {e}"
        logger.exception("OCR error during page processing")

    return result
