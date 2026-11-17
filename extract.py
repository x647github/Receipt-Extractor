"""
extract.py - the command-line tool.

Examples:
  python extract.py samples/ --out receipts.xlsx --offline
  python extract.py my_receipt.jpg --out receipts.csv
"""
import argparse
from pathlib import Path

from checks import check_receipt
from export import save_csv, save_excel, save_json

SUPPORTED = {".pdf", ".png", ".jpg", ".jpeg"}


def find_files(inputs):
    """Turn a mix of files and folders into a sorted list of receipt files."""
    files = []
    for item in map(Path, inputs):
        if item.is_dir():
            files += sorted(p for p in item.iterdir() if p.suffix.lower() in SUPPORTED)
        elif item.suffix.lower() in SUPPORTED:
            files.append(item)
    return files


def process_file(path, offline=False):
    """Extract one receipt and run the checks. Returns a result dict."""
    if offline:
        from offline_extract import extract_offline
        receipt = extract_offline(path)
    else:
        from ai_extract import extract_with_ai
        receipt = extract_with_ai(path)
    return {"file": Path(path).name, "receipt": receipt, "warnings": check_receipt(receipt)}


def main():
    parser = argparse.ArgumentParser(description="Extract data from receipts into Excel/CSV/JSON.")
    parser.add_argument("inputs", nargs="+", help="receipt files or folders")
    parser.add_argument("--out", default="receipts.xlsx", help="output .xlsx or .csv")
    parser.add_argument("--offline", action="store_true", help="no AI: use text + regex")
    args = parser.parse_args()

    results = []
    for path in find_files(args.inputs):
        try:
            res = process_file(path, offline=args.offline)
        except Exception as e:  # one bad file shouldn't stop the others
            print(f"  ERROR  {path.name}: {e}")
            continue
        r = res["receipt"]
        status = "OK" if not res["warnings"] else "CHECK: " + "; ".join(res["warnings"])
        print(f"  {path.name:35} {r.vendor or '?':25} {r.total}  {status}")
        results.append(res)

    if not results:
        print("No receipts processed.")
        return
    out = Path(args.out)
    save_csv(results, out) if out.suffix.lower() == ".csv" else save_excel(results, out)
    save_json(results, out.with_suffix(".json"))
    print(f"Saved {len(results)} receipts to {out} and {out.with_suffix('.json')}")


if __name__ == "__main__":
    main()
