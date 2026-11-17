"""
offline_extract.py - read a receipt WITHOUT any AI (no API key needed).

  1. Get the text:  pdfplumber for PDFs, pytesseract (OCR) for images
  2. Use simple regular expressions ("regex") to find the fields

This is less smart than the AI, but it is free and works for clean receipts.
"""
import re
import string
from datetime import datetime
from pathlib import Path

import pdfplumber

from schema import LineItem, Receipt

# A price like "12.50", "$12.50" or "EUR 12.50"
PRICE = r"(?:\$|EUR\s?|€)?\s?(\d+[.,]\d{2})"


def get_text(path):
    """Return all the text in a PDF or image."""
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        with pdfplumber.open(path) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    try:  # images need OCR (optical character recognition)
        import pytesseract
        from PIL import Image
        return pytesseract.image_to_string(Image.open(path))
    except Exception as e:
        raise RuntimeError(
            f"Can't read image {path.name} offline: install Tesseract OCR, "
            f"or use AI mode. ({e.__class__.__name__})"
        )


def to_number(text):
    return float(text.replace(",", "."))


def find_amount(label, text):
    """Find the price on a line starting with label, e.g. 'TOTAL  $96.73'."""
    match = re.search(rf"^\s*(?:{label})\b.*?{PRICE}\s*$", text, re.IGNORECASE | re.MULTILINE)
    return to_number(match.group(1)) if match else None


def find_date(text):
    """Try a few common date formats and return YYYY-MM-DD."""
    patterns = [
        (r"\d{4}-\d{2}-\d{2}", ["%Y-%m-%d"]),
        (r"\d{1,2}/\d{1,2}/\d{2,4}", ["%m/%d/%Y", "%m/%d/%y"]),
        (r"\d{1,2}\.\d{1,2}\.\d{4}", ["%d.%m.%Y"]),
        (r"[A-Z][a-z]{2} \d{1,2}, \d{4}", ["%b %d, %Y"]),
    ]
    for regex, formats in patterns:
        match = re.search(regex, text)
        if match:
            for fmt in formats:
                try:
                    return datetime.strptime(match.group(0), fmt).strftime("%Y-%m-%d")
                except ValueError:
                    pass
    return None


def find_line_items(text):
    """Lines between the header and SUBTOTAL that end in a price."""
    items = []
    for line in text.splitlines():
        if re.match(r"\s*(SUBTOTAL|TOTAL)\b", line, re.IGNORECASE):
            break  # items are above the totals
        match = re.match(rf"(.+?)\s+{PRICE}\s*$", line)
        if not match:
            continue
        desc, total = match.group(1).strip(), to_number(match.group(2))
        qty, unit = 1, total
        # "Greek Yogurt 4 x 1.50" -> quantity 4, unit price 1.50
        q = re.match(r"(.+?)\s+(\d+)\s*[xX@]\s*(\d+[.,]\d{2})$", desc)
        if q:
            desc, qty, unit = q.group(1), int(q.group(2)), to_number(q.group(3))
        items.append(LineItem(description=desc, quantity=qty, unit_price=unit, total=total))
    return items


def extract_offline(path):
    text = get_text(path)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    currency = "EUR" if ("EUR" in text or "€" in text) else "USD" if "$" in text else None
    return Receipt(
        vendor=string.capwords(lines[0]) if lines else None,  # the store name is usually the first line
        date=find_date(text),
        currency=currency,
        line_items=find_line_items(text),
        subtotal=find_amount("SUBTOTAL", text),
        tax=find_amount("(?:SALES )?TAX|VAT", text),
        tip=find_amount("TIP|GRATUITY", text),
        total=find_amount("(?:GRAND )?TOTAL", text),
    )
