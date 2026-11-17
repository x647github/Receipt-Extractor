"""
export.py - save results to Excel, CSV and JSON.

`results` is a list of dicts: {"file": name, "receipt": Receipt, "warnings": [...]}
"""
import json
from pathlib import Path

import pandas as pd


def to_tables(results):
    """Build two tables: one row per receipt, and one row per line item."""
    summary, items = [], []
    for res in results:
        r = res["receipt"]
        summary.append({
            "file": res["file"], "vendor": r.vendor, "date": r.date, "currency": r.currency,
            "subtotal": r.subtotal, "tax": r.tax, "tip": r.tip, "total": r.total,
            "items": len(r.line_items),
            "check": "OK" if not res["warnings"] else "; ".join(res["warnings"]),
        })
        for item in r.line_items:
            items.append({"file": res["file"], "vendor": r.vendor, **item.model_dump()})
    return pd.DataFrame(summary), pd.DataFrame(items)


def save_excel(results, path):
    summary, items = to_tables(results)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="Receipts", index=False)
        items.to_excel(writer, sheet_name="Line Items", index=False)
        for sheet in writer.sheets.values():  # make columns wide enough to read
            for column in sheet.columns:
                width = max(len(str(cell.value or "")) for cell in column)
                sheet.column_dimensions[column[0].column_letter].width = min(width + 2, 60)


def save_csv(results, path):
    """CSV can only hold one table, so we write two files."""
    summary, items = to_tables(results)
    path = Path(path)
    summary.to_csv(path, index=False)
    items.to_csv(path.with_name(path.stem + "_items.csv"), index=False)


def save_json(results, path):
    data = [{"file": r["file"], "warnings": r["warnings"], **r["receipt"].model_dump()} for r in results]
    Path(path).write_text(json.dumps(data, indent=2))
