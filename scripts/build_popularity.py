"""Generate popularity-by-category data for anonymous-visitor PDP module.

Anonymous visitors have no profile signal beyond the page they're on. We
surface a "Popular in <product_type>" carousel scoped to the same
(index_group, product_type) as the product being viewed, so a man landing
on a t-shirt sees popular Menswear t-shirts (not popular Ladieswear ones
and not generic upper-body items).

This data intentionally does NOT derive from purchase_history_personas.json.
That file models 10 named-persona neighborhoods and would skew popularity
toward those archetypes. Real "store-wide popularity" should reflect the
broader, mostly-anonymous shopper base — so we synthesize fresh, plausible
sales counts here.

Trade-off: keying by product_type_name (vs. the coarser product_group_name)
produces ~143 buckets, ~half of which have ≤2 items. Niche types
(e.g., "Ballerinas") will yield empty carousels after the anchor is
filtered out. Common types (T-shirt, Sweater, Trousers) work great. This
is the right call because relevance >>> coverage for anonymous cold-start.

Approach
--------
Category key = "<index_group_name>::<product_type_name>" (e.g.,
"Menswear::Sweater"). For each bucket:

  1. Score each product by an affinity that combines:
       - a price discount (cheap items genuinely move more units in fast
         fashion: affinity ∝ exp(-price / 40))
       - a sale boost (+0.4 if on sale, scaled by sale_percentage)
       - random noise (uniform(0, 0.6)) so the ordering isn't fully
         determined by price
  2. Sort descending by affinity → rank.
  3. units_sold_30d = round(N0 / rank^s), with N0=5200 and s=1.05.
     Zipfian, because real retail sales are heavily skewed — the #1
     item in a category typically sells 5-10× the median.
     Clamped to [40, 6500] so even rank-tail items have plausible counts.

Output
------
data/popularity_by_category.json:
  {
    "Menswear::Sweater": [
      { "article_id": "0123456789", "units_sold_30d": 4823, "rank": 1 },
      ...
    ],
    ...
  }

Pre-sorted descending so the recommender is just a slice. Seeded for
deterministic output across runs.
"""

from __future__ import annotations

import json
import math
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SEED = 42
random.seed(SEED)

# Zipf parameters. N0 caps the top seller around ~5k units/month, which is
# plausible for a single SKU on a mid-size H&M-style store. s=1.05 gives a
# slightly less steep curve than pure Zipf (s=1) so rank-10 still feels
# like a "popular" item, not noise.
N0 = 5200
ZIPF_S = 1.05
MIN_UNITS = 40
MAX_UNITS = 6500


def affinity(product: dict) -> float:
    """Pseudo-popularity score for ranking within a category bucket."""
    price = product.get("sale_price") or product["price_usd"]
    sale_pct = product.get("sale_percentage") or 0
    price_term = math.exp(-price / 40.0)
    sale_term = 0.4 * (sale_pct / 100.0)
    noise = random.uniform(0.0, 0.6)
    return price_term + sale_term + noise


def units_for_rank(rank: int) -> int:
    raw = N0 / (rank ** ZIPF_S)
    return max(MIN_UNITS, min(MAX_UNITS, round(raw)))


def main() -> None:
    products = json.loads((DATA_DIR / "products.json").read_text())

    # Bucket by (index_group_name, product_type_name).
    buckets: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for p in products:
        key = (p["index_group_name"], p["product_type_name"])
        buckets[key].append(p)

    out: dict[str, list[dict]] = {}
    for (index_group, product_type), items in buckets.items():
        scored = [(affinity(p), p) for p in items]
        scored.sort(key=lambda x: -x[0])
        entries = []
        for rank, (_, p) in enumerate(scored, start=1):
            entries.append(
                {
                    "article_id": p["article_id"],
                    "units_sold_30d": units_for_rank(rank),
                    "rank": rank,
                }
            )
        out[f"{index_group}::{product_type}"] = entries

    out_path = DATA_DIR / "popularity_by_category.json"
    out_path.write_text(json.dumps(out, indent=2))

    # ── Summary ───────────────────────────────────────────────────────
    print(f"Wrote {len(out)} category buckets to {out_path.relative_to(ROOT)}")
    print()
    print(f"{'Category':<48} {'items':>6} {'top units':>10} {'med units':>10}")
    for key in sorted(out.keys()):
        entries = out[key]
        top = entries[0]["units_sold_30d"]
        med = entries[len(entries) // 2]["units_sold_30d"]
        print(f"  {key:<46} {len(entries):>6} {top:>10} {med:>10}")


if __name__ == "__main__":
    main()
