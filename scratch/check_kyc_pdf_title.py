import fitz  # PyMuPDF
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

doc = fitz.open("data/kyc.pdf")
print("Total pages in kyc.pdf:", len(doc))
for pno in range(min(5, len(doc))):
    print(f"=== Page {pno + 1} ===")
    print(doc[pno].get_text()[:600])
    print("-" * 50)
