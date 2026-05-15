"""Sample 600 products from H&M Personalized Fashion Recommendations.

Sampling philosophy
-------------------
A 600-product catalog for a PDP personalization demo has different
constraints than a real-world catalog snapshot. We optimize for:

1.  Wearability. Drop non-fashion product groups (Furniture, Stationery,
    Cosmetic, Interior textile, Garment and Shoe care, Fun, Items, Unknown)
    and any rows whose garment_group is "Unknown" or whose detail_desc is
    empty. The demo is a fashion PDP; cosmetics and furniture would only
    add noise.

2.  Persona pool balance, not proportional realism. The raw catalog is
    ~56% Ladieswear+Baby/Children and only 3% Sport. A proportional sample
    would leave Menswear and Sport-leaning personas with too few candidates
    for "you might also like" to feel personalized. We override with a
    manual per-index_group allocation that gives every adult-shopper persona
    a healthy pool (>=80 products) and keeps Baby/Children at 100 so a
    "parent" persona has gift candidates.

        Ladieswear:    180
        Menswear:      150
        Divided:       100   (H&M's younger / trend-forward line)
        Baby/Children: 100
        Sport:          70
        ------------------
        Total:         600

3.  Within an index_group, stratify by garment_group. This guarantees the
    "Complete the look" carousel can find complementary categories
    (e.g., for a dress, pull shoes + accessories from the same index_group).

4.  Within a (index_group, garment_group) stratum, sample for color
    diversity using a greedy round-robin over perceived_colour_master_name.
    Color affinity is one of the strongest PDP signals, so we want each
    stratum to span as many colors as its pool allows.

5.  Keep the dense_embedding column. It's already computed and is exactly
    what we need for similarity-based "you might also like".

6.  Synthesize a deterministic price_usd from (garment_group, index_group).
    The source dataset has no prices, and price band is a load-bearing
    personalization signal. We fabricate plausible H&M-style prices via a
    seeded hash so prices are stable across runs.

Outputs
-------
- data/products.json       — 600 product records (no embeddings, for the app)
- data/embeddings.json     — { article_id: dense_embedding[] }  (separate file, gitignored)
- data/catalog_stats.json  — summary stats (counts per stratum, color coverage)
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

# ── Config ──────────────────────────────────────────────────────────────────
SEED = 42
TARGET = 600
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# Per-index_group budget. See file-level docstring for rationale.
INDEX_GROUP_BUDGET = {
    "Ladieswear": 180,
    "Menswear": 150,
    "Divided": 100,
    "Baby/Children": 100,
    "Sport": 70,
}
assert sum(INDEX_GROUP_BUDGET.values()) == TARGET

# Product groups that don't belong in a fashion PDP demo.
DROP_PRODUCT_GROUPS = {
    "Furniture", "Stationery", "Cosmetic", "Interior textile",
    "Garment and Shoe care", "Fun", "Items", "Unknown",
}

# Base price (USD) by garment_group — picked to mirror real H&M pricing tiers.
# Multiplied by an index-group factor and jittered deterministically.
GARMENT_BASE_PRICE = {
    "Accessories":            12,
    "Blouses":                24,
    "Dressed":                49,
    "Dresses Ladies":         39,
    "Dresses/Skirts girls":   19,
    "Jersey Basic":           12,
    "Jersey Fancy":           17,
    "Knitwear":               34,
    "Outdoor":                59,
    "Shirts":                 29,
    "Shoes":                  44,
    "Shorts":                 19,
    "Skirts":                 24,
    "Socks and Tights":        7,
    "Special Offers":         12,
    "Swimwear":               19,
    "Trousers":               29,
    "Trousers Denim":         34,
    "Under-, Nightwear":      14,
    "Woven/Jersey/Knitted mix Baby": 16,
    "Unknown":                19,
}
INDEX_GROUP_PRICE_MULT = {
    "Ladieswear":    1.10,
    "Menswear":      1.05,
    "Divided":       0.85,
    "Baby/Children": 0.75,
    "Sport":         1.15,
}


def synth_price(article_id: str, garment: str, index_group: str) -> float:
    """Deterministic price ~ N(base * mult, 25%) via SHA1 of article_id."""
    base = GARMENT_BASE_PRICE.get(garment, 19)
    mult = INDEX_GROUP_PRICE_MULT.get(index_group, 1.0)
    # SHA1 -> [0,1) -> jitter in [0.75, 1.30]
    h = int(hashlib.sha1(article_id.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    jitter = 0.75 + h * 0.55
    raw = base * mult * jitter
    # Round to .99 endings, H&M style
    return float(f"{int(raw) + 0.99:.2f}")


# ── Load ────────────────────────────────────────────────────────────────────
print("Loading H&M dataset from Hugging Face …")
df = pd.read_parquet(
    "hf://datasets/Qdrant/hm_ecommerce_products/hm_ecommerce_products_enriched.parquet"
)
print(f"  loaded {len(df):,} rows, {df.shape[1]} cols")

# ── Filter to fashion-relevant rows with good metadata ─────────────────────
before = len(df)
df = df[~df["product_group_name"].isin(DROP_PRODUCT_GROUPS)]
df = df[df["garment_group_name"] != "Unknown"]
df = df[df["detail_desc"].notna() & (df["detail_desc"].str.len() > 20)]
df = df[df["image_url"].notna()]
print(f"  filtered: {before:,} -> {len(df):,} ({before - len(df):,} dropped)")

# ── Stratified allocation: per index_group, distribute over garment_group ─
rng = np.random.default_rng(SEED)
selected_ids: list[str] = []

allocation_report = []
for index_group, budget in INDEX_GROUP_BUDGET.items():
    pool = df[df["index_group_name"] == index_group]
    garment_counts = pool["garment_group_name"].value_counts()

    # Allocate budget across garment_groups proportional to log(pool_size).
    # Log dampens dominant garments so smaller ones still get representation.
    weights = np.log1p(garment_counts.values)
    weights = weights / weights.sum()
    raw_alloc = weights * budget
    floor = np.floor(raw_alloc).astype(int)
    # Ensure every garment_group present gets at least 1, capped at pool size.
    floor = np.maximum(floor, 1)
    floor = np.minimum(floor, garment_counts.values)
    # Top up by largest remainder until we hit budget exactly.
    remainder = raw_alloc - floor
    deficit = budget - floor.sum()
    if deficit > 0:
        room = garment_counts.values - floor
        candidates = np.argsort(-remainder)
        for idx in candidates:
            if deficit == 0:
                break
            if room[idx] > 0:
                floor[idx] += 1
                room[idx] -= 1
                deficit -= 1
    elif deficit < 0:
        # Over-allocated: remove from largest cells first.
        excess = -deficit
        order = np.argsort(-floor)
        for idx in order:
            if excess == 0:
                break
            take = min(floor[idx] - 1, excess)  # leave at least 1
            floor[idx] -= take
            excess -= take

    alloc = dict(zip(garment_counts.index, floor.tolist()))
    assert sum(alloc.values()) == budget, (index_group, sum(alloc.values()), budget)

    # ── Within each garment_group, sample with color round-robin ─────────
    for garment, n in alloc.items():
        if n == 0:
            continue
        cell = pool[pool["garment_group_name"] == garment]
        # Group by master color, shuffle within each color, then round-robin.
        groups = {
            color: cell[cell["perceived_colour_master_name"] == color]
                    .sample(frac=1, random_state=SEED)["article_id"].tolist()
            for color in cell["perceived_colour_master_name"].unique()
        }
        # Shuffle color order itself for variety.
        color_order = list(groups.keys())
        rng.shuffle(color_order)

        picked: list[str] = []
        i = 0
        while len(picked) < n and any(groups.values()):
            color = color_order[i % len(color_order)]
            if groups[color]:
                picked.append(groups[color].pop())
            i += 1
        selected_ids.extend(picked)
        allocation_report.append({
            "index_group": index_group,
            "garment_group": garment,
            "pool_size": int(len(cell)),
            "sampled": int(len(picked)),
            "unique_colors": int(cell["perceived_colour_master_name"].nunique()),
        })

assert len(selected_ids) == TARGET, len(selected_ids)
print(f"  selected exactly {len(selected_ids)} products")

# ── Build final dataframe ──────────────────────────────────────────────────
sample = df[df["article_id"].isin(selected_ids)].copy()
# Preserve our pick order for reproducibility.
sample = sample.set_index("article_id").loc[selected_ids].reset_index()

# Synthesize price.
sample["price_usd"] = sample.apply(
    lambda r: synth_price(r["article_id"], r["garment_group_name"], r["index_group_name"]),
    axis=1,
)

# ── Split embeddings into a separate file ──────────────────────────────────
embeddings = {
    row["article_id"]: list(row["dense_embedding"])
    for _, row in sample.iterrows()
}

product_cols = [
    "article_id", "product_code", "prod_name",
    "product_type_name", "product_group_name", "garment_group_name",
    "graphical_appearance_name", "colour_group_name",
    "perceived_colour_value_name", "perceived_colour_master_name",
    "department_name", "index_name", "index_group_name", "section_name",
    "detail_desc", "image_url", "price_usd",
]
products = sample[product_cols].to_dict(orient="records")

# ── Persist ────────────────────────────────────────────────────────────────
(DATA_DIR / "products.json").write_text(json.dumps(products, indent=2))
(DATA_DIR / "embeddings.json").write_text(json.dumps(embeddings))

stats = {
    "total": len(products),
    "by_index_group": sample["index_group_name"].value_counts().to_dict(),
    "by_product_group": sample["product_group_name"].value_counts().to_dict(),
    "by_garment_group": sample["garment_group_name"].value_counts().to_dict(),
    "unique_colors": int(sample["perceived_colour_master_name"].nunique()),
    "unique_product_types": int(sample["product_type_name"].nunique()),
    "price_usd": {
        "min": float(sample["price_usd"].min()),
        "median": float(sample["price_usd"].median()),
        "max": float(sample["price_usd"].max()),
    },
    "allocation_report": allocation_report,
}
(DATA_DIR / "catalog_stats.json").write_text(json.dumps(stats, indent=2))

# ── Summary ────────────────────────────────────────────────────────────────
print("\n=== Catalog summary ===")
print(f"products.json:    {len(products)} rows")
print(f"embeddings.json:  {len(embeddings)} vectors, dim={len(next(iter(embeddings.values())))}")
print(f"unique colors:    {stats['unique_colors']}")
print(f"unique types:     {stats['unique_product_types']}")
print(f"price range:      ${stats['price_usd']['min']:.2f} - ${stats['price_usd']['max']:.2f} "
      f"(median ${stats['price_usd']['median']:.2f})")
print("\nby index_group:")
for k, v in sorted(stats["by_index_group"].items(), key=lambda x: -x[1]):
    print(f"  {k:<16} {v:>4}")
print("\nby product_group:")
for k, v in sorted(stats["by_product_group"].items(), key=lambda x: -x[1]):
    print(f"  {k:<22} {v:>4}")
