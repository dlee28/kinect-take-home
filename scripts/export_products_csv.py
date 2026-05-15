"""Export data/products.json → data/prod_chat.csv with a simplified schema.

Column mapping (everything else in the JSON is dropped):
  article_id        → prod_id
  prod_name         → name
  price_usd         → price
  product_type_name → category
  detail_desc       → description

Run: python3 scripts/export_products_csv.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

products = json.loads((DATA_DIR / "products.json").read_text())

out_path = DATA_DIR / "prod_chat.csv"
fieldnames = ["prod_id", "name", "price", "category", "description"]

with out_path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for p in products:
        writer.writerow(
            {
                "prod_id": p["article_id"],
                "name": p["prod_name"],
                "price": p["price_usd"],
                "category": p["product_type_name"],
                "description": p["detail_desc"],
            }
        )

print(f"Wrote {len(products)} rows → {out_path.relative_to(ROOT)}")
