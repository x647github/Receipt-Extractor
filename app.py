"""
app.py - a simple web page for the receipt extractor.

Run:  streamlit run app.py
Then open the link it prints (usually http://localhost:8501).
"""
import os
import tempfile
from io import BytesIO
from pathlib import Path

import streamlit as st

from export import save_excel, to_tables
from extract import SUPPORTED, process_file

st.set_page_config(page_title="AI Receipt Extractor", page_icon="🧾", layout="wide")


def check_password():
    """Ask for a password if APP_PASSWORD is set in Secrets. Returns True when OK."""
    password = os.getenv("APP_PASSWORD")
    if not password:  # no password set (e.g. on your own Mac): let everyone in
        return True
    if st.session_state.get("logged_in"):
        return True
    st.title("🔒 AI Receipt Extractor")
    entered = st.text_input("Demo password", type="password")
    if entered:
        if entered == password:
            st.session_state["logged_in"] = True
            st.rerun()
        else:
            st.error("Wrong password")
    return False


if not check_password():
    st.stop()  # don't show the rest of the app
st.title("🧾 AI Receipt Extractor")
st.write("Upload receipts (PDF, PNG, JPG). Get a clean table and an Excel file.")

# Sidebar: choose AI or offline mode.
has_key = bool(os.getenv("OPENAI_API_KEY"))
offline = st.sidebar.toggle("Offline mode (no AI)", value=not has_key,
                            help="Offline mode reads text from PDFs with simple rules. "
                                 "AI mode needs OPENAI_API_KEY and can read photos.")
st.sidebar.caption("AI key found ✅" if has_key else "No OPENAI_API_KEY set: using offline mode.")
use_samples = st.sidebar.checkbox("Try the sample receipts")

uploads = st.file_uploader("Receipts", type=[s.strip(".") for s in SUPPORTED],
                           accept_multiple_files=True)

# Collect (name, path) pairs. Uploaded files are saved to a temp folder first.
files = []
tmp_dir = Path(tempfile.mkdtemp())
for up in uploads or []:
    path = tmp_dir / up.name
    path.write_bytes(up.getvalue())
    files.append(path)
if use_samples:
    files += sorted(Path("samples").glob("*.pdf"))

if files:
    results = []
    with st.spinner(f"Reading {len(files)} receipt(s)..."):
        for path in files:
            try:
                results.append(process_file(path, offline=offline))
            except Exception as e:
                st.error(f"{path.name}: {e}")

    if results:
        summary, items = to_tables(results)
        bad = [r for r in results if r["warnings"]]
        col1, col2, col3 = st.columns(3)
        col1.metric("Receipts", len(results))
        col2.metric("Line items", len(items))
        col3.metric("Need review", len(bad))

        buffer = BytesIO()
        save_excel(results, buffer)  # write the Excel file into memory
        st.download_button("⬇️ Download Excel", buffer.getvalue(), "receipts.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # Show money with 2 decimals (34.30 instead of 34.3)
        money = {c: st.column_config.NumberColumn(format="%.2f")
                 for c in ["subtotal", "tax", "tip", "total", "unit_price"]}
        st.subheader("Receipts")
        st.dataframe(summary, use_container_width=True, hide_index=True, column_config=money)
        for r in bad:
            st.warning(f"{r['file']}: " + "; ".join(r["warnings"]))

        with st.expander("Line items"):
            st.dataframe(items, use_container_width=True, hide_index=True, column_config=money)

else:
    st.info("Upload a receipt, or tick **Try the sample receipts** in the sidebar.")
