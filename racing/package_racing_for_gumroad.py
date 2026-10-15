#!/usr/init/env python3
"""
Package FormFav Racing Intelligence into an official Gumroad product bundle.
"""
import zipfile
import os
from pathlib import Path

DATE_GUIDE = "2026-10-09"
DATE_SUB = "2026-10-08"

pdf_path = Path(f"outputs/formfav/{DATE_GUIDE}/AUS_GALLOPS_FORM_GUIDE_{DATE_GUIDE}.pdf")
bulletin_path = Path(f"outputs/formfav/{DATE_SUB}/AUS_RACES_PREDICTIONS_{DATE_SUB}.md")
sales_copy_path = Path(f"outputs/formfav/{DATE_SUB}/racing_sales_copy.md")

out_zip = Path("outputs/formfav_racing_intelligence_gumroad_package.zip")

with zipfile.ZipFile(out_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
    if pdf_path.exists():
        zf.write(pdf_path, f"form_guide_{DATE_GUIDE}.pdf")
    if bulletin_path.exists():
        zf.write(bulletin_path, f"race_predictions_{DATE_SUB}.md")
    if sales_copy_path.exists():
        zf.write(sales_copy_path, "sales_copy.md")

print(f"✅ Created official Gumroad Racing Intelligence package: {out_zip} ({out_zip.stat().st_size:,} bytes)")
