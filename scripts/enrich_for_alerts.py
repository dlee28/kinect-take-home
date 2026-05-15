"""Enrich products with stock + sale fields, and rewrite each persona's
wishlist as structured entries with snapshot fields (price_at_add,
stock_at_add_in_my_size). One seeded pass keeps the two sides consistent.

Run after sample_catalog.py and build_personas.py. This step is what
makes the wishlist-alerts demo actually fire: persona snapshots are
backfilled to values that are deliberately *higher than current* for
items meant to trigger alerts, so the comparison
`current < snapshot` lights up for the right items.
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SEED = 91
random.seed(SEED)
REFERENCE_DATE = datetime(2026, 5, 12)

# Personas excluded from the alert-firing bias. Their wishlist items
# stay at list price and at original stock, so the wishlist-alerts
# module returns zero alerts for them. Useful for demonstrating that
# the module degrades gracefully when nothing has changed since add.
EXCLUDE_FROM_ALERTS = {"0001"}   # Ana — see persona definition for name

# ── Size mapping ─────────────────────────────────────────────────────────
# Maps garment_group_name → (size scale, persona declared-size field)
ALPHA_SIZES = ["XS", "S", "M", "L", "XL"]
WAIST_SIZES = ["24", "26", "28", "30", "32", "34", "36"]
SHOE_SIZES = ["6", "7", "8", "9", "10", "11", "12"]

ALPHA_GROUPS = {
    "Jersey Fancy", "Jersey Basic", "Blouses", "Knitwear", "Shirts",
    "Outdoor", "Dressed", "Under-, Nightwear", "Dresses Ladies",
    "Dresses/Skirts girls",
}
WAIST_GROUPS = {"Trousers", "Trousers Denim", "Skirts", "Shorts", "Swimwear"}
SHOE_GROUPS = {"Shoes"}
ONE_SIZE_GROUPS = {
    "Accessories", "Socks and Tights", "Woven/Jersey/Knitted mix Baby",
    "Special Offers",
}


def size_scale_for(garment_group: str) -> tuple[list[str], str | None]:
    """Return (sizes, persona-field). persona-field is None for one-size."""
    if garment_group in ALPHA_GROUPS:
        return ALPHA_SIZES, "top"
    if garment_group in WAIST_GROUPS:
        return WAIST_SIZES, "bottom"
    if garment_group in SHOE_GROUPS:
        return SHOE_SIZES, "shoe"
    return ["ONE_SIZE"], None


# ── Load ─────────────────────────────────────────────────────────────────
products = json.loads((DATA_DIR / "products.json").read_text())
personas = json.loads((DATA_DIR / "personas.json").read_text())
products_by_id = {p["article_id"]: p for p in products}

# Collect every article_id any *alert-eligible* persona has wishlisted.
# Personas in EXCLUDE_FROM_ALERTS contribute nothing to the sale-bias set —
# so their items will rarely end up on sale, and won't get forced low-stock.
wishlist_article_ids: set[str] = set()
for persona in personas:
    if persona.get("shopper_id") in EXCLUDE_FROM_ALERTS:
        continue
    wl = persona.get("browse_history", {}).get("wishlist", []) if persona.get("browse_history") else []
    for entry in wl:
        if isinstance(entry, str):
            wishlist_article_ids.add(entry)
        elif isinstance(entry, dict) and "article_id" in entry:
            # Idempotent re-run support: already structured.
            wishlist_article_ids.add(entry["article_id"])

# ── Step 0: clear any sale fields from prior runs ─────────────────────────
# Without this, re-running the script ACCUMULATES sale_price markers on
# products from previous runs whose exclusion settings may have differed.
for product in products:
    product.pop("sale_price", None)
    product.pop("sale_percentage", None)

# ── Step 1: baseline stock_by_size for every product ─────────────────────
for product in products:
    sizes, _ = size_scale_for(product["garment_group_name"])
    product["stock_by_size"] = {s: random.randint(15, 50) for s in sizes}

# Step 1b: force low stock at *the persona's declared size* for ~50% of
# their wishlist items. This is what makes the low-stock alert demo fire.
# A (article_id, size) pair gets flagged so the snapshot backfill knows to
# record a "before" stock higher than the current low value.
forced_low_pairs: set[tuple[str, str]] = set()

for persona in personas:
    if persona.get("shopper_id") in EXCLUDE_FROM_ALERTS:
        continue
    bh = persona.get("browse_history")
    if not bh:
        continue
    declared_sizes = persona.get("declared", {}).get("sizes", {})
    for entry in bh.get("wishlist", []):
        article_id = entry if isinstance(entry, str) else entry.get("article_id")
        if not article_id:
            continue
        p = products_by_id.get(article_id)
        if not p:
            continue
        sizes, field = size_scale_for(p["garment_group_name"])
        if field is None:
            continue
        declared_size = declared_sizes.get(field)
        if not declared_size or declared_size not in sizes:
            continue
        if random.random() < 0.5:
            p["stock_by_size"][declared_size] = random.randint(1, 3)
            forced_low_pairs.add((article_id, declared_size))

# ── Step 2: pick 20 sale items biased to Upper-body wishlist ─────────────
# Excluded personas' wishlist items are blocked from the sale set entirely
# so their alert preview is deterministically zero.
excluded_wishlist_ids: set[str] = set()
for persona in personas:
    if persona.get("shopper_id") not in EXCLUDE_FROM_ALERTS:
        continue
    wl = persona.get("browse_history", {}).get("wishlist", []) if persona.get("browse_history") else []
    for entry in wl:
        article_id = entry if isinstance(entry, str) else entry.get("article_id")
        if article_id:
            excluded_wishlist_ids.add(article_id)

UPPER_BODY = [p for p in products if p["product_group_name"] == "Garment Upper body"]
wishlist_upper = [p for p in UPPER_BODY if p["article_id"] in wishlist_article_ids]

# All wishlist-Upper-body get sale; fill the rest from random Upper body.
sale_set: dict[str, dict] = {}
remaining = 20 - len(wishlist_upper)
for p in wishlist_upper:
    sale_set[p["article_id"]] = p
if remaining > 0:
    pool = [
        p for p in UPPER_BODY
        if p["article_id"] not in sale_set
        and p["article_id"] not in excluded_wishlist_ids
    ]
    random.shuffle(pool)
    for p in pool[:remaining]:
        sale_set[p["article_id"]] = p
elif remaining < 0:
    # More wishlist-upper items than 20 slots — keep all wishlist hits, no fill.
    pass

for article_id, p in sale_set.items():
    discount = random.randint(20, 50)  # 20-50% off
    sale_price = int(p["price_usd"] * (1 - discount / 100)) + 0.99
    p["sale_price"] = round(sale_price, 2)
    p["sale_percentage"] = discount

# ── Step 3: rewrite persona wishlists as structured WishlistEntry list ──
for persona in personas:
    bh = persona.get("browse_history")
    if not bh:
        continue
    old_wl = bh.get("wishlist", [])
    declared_sizes = persona.get("declared", {}).get("sizes", {})
    new_wl: list[dict] = []

    for entry in old_wl:
        article_id = entry if isinstance(entry, str) else entry.get("article_id")
        if not article_id:
            continue
        product = products_by_id.get(article_id)
        if not product:
            continue

        # added_at: random 30-180 days before reference
        days_ago = random.randint(30, 180)
        added_at = (REFERENCE_DATE - timedelta(days=days_ago)).isoformat()

        # price_at_add = list price (not sale_price). Guarantees that if
        # the item is currently on sale, the alert fires.
        price_at_add = float(product["price_usd"])

        # stock_at_add: only if the persona has a declared size that
        # matches the garment-group's scale.
        sizes, field = size_scale_for(product["garment_group_name"])
        stock_snapshot: int | None = None
        if field is not None:
            declared_size = declared_sizes.get(field)
            if declared_size is not None and declared_size in sizes:
                current = product["stock_by_size"].get(declared_size, 0)
                # If we forced low stock at the persona's size, snapshot a
                # value above current so the alert fires.
                if (article_id, declared_size) in forced_low_pairs:
                    stock_snapshot = random.randint(15, 30)
                else:
                    stock_snapshot = current

        new_entry: dict = {
            "article_id": article_id,
            "added_at": added_at,
            "price_at_add": price_at_add,
        }
        if stock_snapshot is not None:
            new_entry["stock_at_add_in_my_size"] = stock_snapshot
        new_wl.append(new_entry)

    bh["wishlist"] = new_wl

# ── Persist ──────────────────────────────────────────────────────────────
(DATA_DIR / "products.json").write_text(json.dumps(products, indent=2))
(DATA_DIR / "personas.json").write_text(json.dumps(personas, indent=2))

# ── Summary ──────────────────────────────────────────────────────────────
print(f"Products: {len(products)} total")
print(f"  on sale: {len(sale_set)} (all in Garment Upper body)")
print(f"  with stock_by_size: {sum(1 for p in products if p.get('stock_by_size'))}")
print(f"  forced low-stock (article, size) pairs: {len(forced_low_pairs)}")
print()
print("Per-persona alert preview:")
for persona in personas:
    sid = persona.get("shopper_id")
    bh = persona.get("browse_history")
    if not bh:
        print(f"  {sid:<12} (no wishlist)")
        continue
    wl = bh.get("wishlist", [])
    sale_n = 0
    low_n = 0
    declared_sizes = persona.get("declared", {}).get("sizes", {})
    for entry in wl:
        p = products_by_id.get(entry["article_id"])
        if not p:
            continue
        current_price = p.get("sale_price", p["price_usd"])
        if current_price < entry["price_at_add"]:
            sale_n += 1
        sizes, field = size_scale_for(p["garment_group_name"])
        if (
            field
            and "stock_at_add_in_my_size" in entry
            and declared_sizes.get(field) in sizes
        ):
            declared_size = declared_sizes[field]
            current_stock = p["stock_by_size"].get(declared_size, 999)
            if (
                1 <= current_stock <= 3
                and current_stock < entry["stock_at_add_in_my_size"]
            ):
                low_n += 1
    print(f"  {sid:<12} wishlist={len(wl)}  sale_alerts={sale_n}  low_stock_alerts={low_n}")
