"""Generate 100 synthetic purchase-history customers for the
"Customers like you bought" carousel pool.

These are NOT switchable demo profiles. They exist only so the
recommendation carousel has a real customer base to surface from.
Each customer has only the schema fields needed for matching:

  - demographics (gender_presentation, age_band, climate)
  - declared (style_archetypes, value_priorities, material_avoid)
  - affinities (index_groups, garment_groups, colors, price_band) — computed
  - segments
  - purchase_history (orders + aggregates incl. total_items_purchased)
  - session (filled with sentinel "direct/desktop" — required by ShopperProfile,
    not used by the recommender for history customers)

Approach
--------
Define 10 archetypes (customer segments). For each archetype, generate
10 customers with realistic intra-archetype variation:
  - age_band sampled from a permitted set
  - 2-15 orders (Poisson(5), clipped)
  - 1-4 items per order
  - items drawn from data/products.json matching the archetype's
    product predicate (so all article_ids resolve)
  - segments: 1-3 sampled from the archetype's segments pool

The 10 archetypes intentionally cover the 5 named-persona
neighborhoods plus 5 generic neighborhoods, so every named persona
has a few real neighbors and a fallback pool for relaxation.
"""

from __future__ import annotations

import json
import random
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SEED = 21
random.seed(SEED)

products = json.loads((DATA_DIR / "products.json").read_text())
products_by_id = {p["article_id"]: p for p in products}


# ── Helpers (similar shape to scripts/build_personas.py) ─────────────────
def iso_days_ago(d: int) -> str:
    base = datetime(2026, 5, 12)
    return (base - timedelta(days=d)).isoformat()


def pick(predicate, k, exclude=()):
    pool = [p for p in products if predicate(p) and p["article_id"] not in exclude]
    random.shuffle(pool)
    return [p["article_id"] for p in pool[:k]]


def compute_affinities(article_ids):
    if not article_ids:
        return None
    idx = Counter()
    prices = []
    for aid in article_ids:
        p = products_by_id.get(aid)
        if p is None:
            continue
        idx[p["index_group_name"]] += 1
        prices.append(p["price_usd"])
    total = sum(idx.values()) or 1
    index_groups = {k: round(v / total, 3) for k, v in idx.most_common()}
    prices.sort()
    n = len(prices)
    price_band = {
        "p25": round(prices[max(0, n // 4)], 2),
        "median": round(prices[n // 2], 2),
        "p75": round(prices[min(n - 1, (3 * n) // 4)], 2),
    } if prices else {"p25": 0.0, "median": 0.0, "p75": 0.0}
    return {"index_groups": index_groups, "price_band": price_band}


def build_order(_order_idx: int, days_ago: int, article_ids):
    """In-memory order. Only article_ids survives serialization; `_placed_at`
    is consumed by aggregate_orders and stripped before write."""
    return {
        "article_ids": list(article_ids),
        "_placed_at": iso_days_ago(days_ago),
    }


def aggregate_orders(orders, return_rate=0.0):
    placed = sum(len(o["article_ids"]) for o in orders)
    last = max((o["_placed_at"] for o in orders), default=None)
    return {
        "total_items_purchased": placed,
        "last_order_at": last,
        "return_rate": return_rate,
    }


def strip_internal_order_fields(customer: dict) -> None:
    ph = customer.get("purchase_history")
    if not ph:
        return
    for order in ph.get("orders", []):
        for key in list(order.keys()):
            if key.startswith("_"):
                del order[key]


# Keyword sets used to keep vegan archetypes' purchases consistent with their
# material_avoid (we filter them out at picking time, not after).
MATERIAL_KEYWORDS = {
    "wool":    ["wool", "merino"],
    "leather": ["leather", "suede"],
    "silk":    ["silk", "satin"],
    "fur":     ["fur", "fluff", "shearling"],
}


def violates_materials(product, avoid_list):
    if not avoid_list:
        return False
    desc = (product.get("detail_desc") or "").lower()
    for m in avoid_list:
        for kw in MATERIAL_KEYWORDS.get(m, [m]):
            if kw in desc:
                return True
    return False


# ── Archetype definitions ────────────────────────────────────────────────
# Each archetype is a recipe: gender, climate, styles, segments pool, value
# priorities, and a product predicate that defines what they buy.
ARCHETYPES = [
    {
        "id": "fem_ladies_classic",
        "label": "Feminine Ladieswear classic/minimalist (Ana neighborhood)",
        "gender_presentation": "feminine",
        "age_bands": ["25-34", "35-44", "45-54"],
        "climate": "temperate",
        "style_archetypes": ["classic", "minimalist"],
        "material_avoid": [],
        "value_priorities": {"quality": 1, "comfort": 2, "sustainability": 3, "price": 4, "trend": 5},
        "segments_pool": ["repeat_buyer", "low_returner", "newsletter_engaged", "gold_tier"],
        "predicate": lambda p: (
            p["index_group_name"] == "Ladieswear"
            and p["perceived_colour_master_name"] in {"Beige", "Black", "White", "Grey", "Brown"}
            and p["price_usd"] >= 25
        ),
    },
    {
        "id": "masc_menswear_streetwear",
        "label": "Masculine Menswear streetwear/trend (Marcus neighborhood)",
        "gender_presentation": "masculine",
        "age_bands": ["18-24", "25-34"],
        "climate": "temperate",
        "style_archetypes": ["streetwear", "trend"],
        "material_avoid": [],
        "value_priorities": {"trend": 1, "price": 2, "comfort": 3, "quality": 4, "sustainability": 5},
        "segments_pool": ["browse_heavy", "social_referral", "gen_z", "first_year_customer"],
        "predicate": lambda p: (
            p["index_group_name"] in {"Menswear", "Divided"}
            and p["price_usd"] <= 45
            and p["garment_group_name"] in {"Jersey Fancy", "Jersey Basic", "Trousers Denim", "Shirts", "Shoes", "Knitwear", "Outdoor"}
        ),
    },
    {
        "id": "fem_parent_value",
        "label": "Feminine Ladies+Baby parent, hot climate (Priya neighborhood)",
        "gender_presentation": "feminine",
        "age_bands": ["25-34", "35-44"],
        "climate": "hot",
        "style_archetypes": ["athleisure", "minimalist"],
        "material_avoid": ["wool"],
        "value_priorities": {"price": 1, "quality": 2, "comfort": 3, "sustainability": 4, "trend": 5},
        "segments_pool": ["new_parent", "multi_shopper_household", "value_seeker", "returns_high"],
        "predicate": lambda p: (
            p["index_group_name"] in {"Baby/Children", "Ladieswear"}
            and p["garment_group_name"] not in {"Knitwear", "Outdoor"}
            and p["price_usd"] <= 35
            and not violates_materials(p, ["wool"])
        ),
    },
    {
        "id": "masc_sport_outdoor",
        "label": "Masculine Sport+Menswear outdoor, cold climate (Diego neighborhood)",
        "gender_presentation": "masculine",
        "age_bands": ["25-34", "35-44", "45-54"],
        "climate": "cold",
        "style_archetypes": ["athleisure", "classic"],
        "material_avoid": [],
        "value_priorities": {"comfort": 1, "quality": 2, "price": 3, "sustainability": 4, "trend": 5},
        "segments_pool": ["long_tenured", "outdoor_enthusiast", "low_returner", "gold_tier"],
        "predicate": lambda p: (
            p["index_group_name"] in {"Sport", "Menswear"}
            and p["garment_group_name"] in {"Outdoor", "Knitwear", "Shoes", "Trousers", "Jersey Fancy", "Jersey Basic"}
            and p["price_usd"] >= 25
        ),
    },
    {
        "id": "fem_vegan_divided",
        "label": "Feminine Divided/Ladies vegan, budget (Yuki neighborhood)",
        "gender_presentation": "feminine",
        "age_bands": ["18-24", "25-34"],
        "climate": "temperate",
        "style_archetypes": ["minimalist", "bohemian"],
        "material_avoid": ["wool", "leather", "silk", "fur"],
        "value_priorities": {"sustainability": 1, "price": 2, "quality": 3, "comfort": 4, "trend": 5},
        "segments_pool": ["values_led", "first_year_customer", "gen_z", "newsletter_engaged"],
        "predicate": lambda p: (
            p["index_group_name"] in {"Divided", "Ladieswear"}
            and p["price_usd"] <= 32
            and p["garment_group_name"] != "Shoes"
            and not violates_materials(p, ["wool", "leather", "silk", "fur"])
        ),
    },
    {
        "id": "masc_menswear_classic",
        "label": "Masculine Menswear classic, temperate, mid-band (generic)",
        "gender_presentation": "masculine",
        "age_bands": ["35-44", "45-54", "55+"],
        "climate": "temperate",
        "style_archetypes": ["classic", "preppy"],
        "material_avoid": [],
        "value_priorities": {"quality": 1, "comfort": 2, "price": 3, "sustainability": 4, "trend": 5},
        "segments_pool": ["repeat_buyer", "low_returner", "newsletter_engaged"],
        "predicate": lambda p: (
            p["index_group_name"] == "Menswear"
            and p["garment_group_name"] in {"Shirts", "Trousers", "Knitwear", "Jersey Basic", "Outdoor"}
            and 25 <= p["price_usd"] <= 60
        ),
    },
    {
        "id": "fem_athleisure",
        "label": "Feminine athleisure, temperate, mid-band (generic)",
        "gender_presentation": "feminine",
        "age_bands": ["18-24", "25-34", "35-44"],
        "climate": "temperate",
        "style_archetypes": ["athleisure", "trend"],
        "material_avoid": [],
        "value_priorities": {"quality": 1, "comfort": 2, "price": 3, "trend": 4, "sustainability": 5},
        "segments_pool": ["browse_heavy", "newsletter_engaged", "fitness_segment"],
        "predicate": lambda p: (
            p["index_group_name"] in {"Ladieswear", "Sport", "Divided"}
            and p["garment_group_name"] in {"Jersey Fancy", "Jersey Basic", "Trousers", "Shorts", "Shoes"}
            and p["price_usd"] <= 45
        ),
    },
    {
        "id": "fem_baby_focus",
        "label": "Feminine Baby/Children focused (generic)",
        "gender_presentation": "feminine",
        "age_bands": ["25-34", "35-44"],
        "climate": "temperate",
        "style_archetypes": ["classic", "minimalist"],
        "material_avoid": [],
        "value_priorities": {"price": 1, "quality": 2, "comfort": 3, "sustainability": 4, "trend": 5},
        "segments_pool": ["new_parent", "multi_shopper_household", "value_seeker"],
        "predicate": lambda p: (
            p["index_group_name"] == "Baby/Children"
            and p["price_usd"] <= 25
        ),
    },
    {
        "id": "masc_divided_trend",
        "label": "Masculine Divided trend, warm climate, budget (generic)",
        "gender_presentation": "masculine",
        "age_bands": ["18-24"],
        "climate": "hot",
        "style_archetypes": ["streetwear", "trend"],
        "material_avoid": [],
        "value_priorities": {"trend": 1, "price": 2, "comfort": 3, "quality": 4, "sustainability": 5},
        "segments_pool": ["browse_heavy", "gen_z", "social_referral", "first_year_customer"],
        "predicate": lambda p: (
            p["index_group_name"] in {"Divided", "Menswear"}
            and p["price_usd"] <= 30
            and p["garment_group_name"] in {"Jersey Fancy", "Jersey Basic", "Shorts", "Swimwear", "Shoes"}
        ),
    },
    {
        "id": "neutral_minimalist_premium",
        "label": "Neutral minimalist, premium (generic)",
        "gender_presentation": "neutral",
        "age_bands": ["25-34", "35-44"],
        "climate": "temperate",
        "style_archetypes": ["minimalist", "classic"],
        "material_avoid": [],
        "value_priorities": {"quality": 1, "sustainability": 2, "comfort": 3, "price": 4, "trend": 5},
        "segments_pool": ["values_led", "low_returner", "gold_tier", "newsletter_engaged"],
        "predicate": lambda p: (
            p["perceived_colour_master_name"] in {"Black", "White", "Grey", "Beige"}
            and p["price_usd"] >= 35
        ),
    },
]


# ── Generation ───────────────────────────────────────────────────────────
CUSTOMERS_PER_ARCHETYPE = 10
customers = []
order_counter = 0
empty_predicates = []

for a_idx, arche in enumerate(ARCHETYPES):
    # Sanity check: how many products satisfy this predicate at all?
    pool_size = sum(1 for p in products if arche["predicate"](p))
    if pool_size == 0:
        empty_predicates.append(arche["id"])
        continue

    for c_idx in range(CUSTOMERS_PER_ARCHETYPE):
        # Order count ~ Poisson(5), clipped to [2, 15]. Use simple gamma-distribution proxy.
        n_orders = max(2, min(15, int(random.gauss(5, 2.5))))
        orders = []
        purchased_in_session = set()

        # Spread orders across last ~365 days.
        order_dates = sorted(random.sample(range(5, 360), n_orders))
        for o_offset_idx, days_ago in enumerate(order_dates):
            items_per_order = random.randint(1, 4)
            picked = pick(arche["predicate"], items_per_order, exclude=purchased_in_session)
            if not picked:
                continue
            purchased_in_session.update(picked)
            order_counter += 1
            orders.append(build_order(order_counter, days_ago, picked))

        if not orders:
            # Shouldn't happen given pool_size > 0, but guard.
            continue

        all_article_ids = [aid for o in orders for aid in o["article_ids"]]
        aff = compute_affinities(all_article_ids)
        # ~20% of customers are high-returners. Gives the -2 return_rate
        # penalty in the recommender something to fire on.
        return_rate = round(random.uniform(0.35, 0.55), 2) if random.random() < 0.2 else 0.0
        aggregates = aggregate_orders(orders, return_rate=return_rate)

        cust = {
            "shopper_id": f"ph_{a_idx:02d}_{c_idx:02d}",
            "display_name": f"{arche['id']}_{c_idx:02d}",
            "demographics": {
                "age_band": random.choice(arche["age_bands"]),
                "gender_presentation": arche["gender_presentation"],
                "location": {"climate": arche["climate"]},
            },
            "declared": {
                "sizes": {},
                "style_archetypes": list(arche["style_archetypes"]),
                "value_priorities": dict(arche["value_priorities"]),
                **({"material_avoid": list(arche["material_avoid"])} if arche["material_avoid"] else {}),
            },
            "purchase_history": {"orders": orders, "aggregates": aggregates},
            "segments": random.sample(arche["segments_pool"], k=min(3, len(arche["segments_pool"]))),
            "affinities": aff,
        }
        customers.append(cust)

if empty_predicates:
    raise RuntimeError(f"Archetypes with empty product pool: {empty_predicates}")

# ── Strip sidecar order fields, then write ──────────────────────────────
for c in customers:
    strip_internal_order_fields(c)

out_path = DATA_DIR / "purchase_history_personas.json"
out_path.write_text(json.dumps(customers, indent=2))


# ── Summary ──────────────────────────────────────────────────────────────
total_items = sum(c["purchase_history"]["aggregates"]["total_items_purchased"] for c in customers)
print(f"Wrote {len(customers)} customers to {out_path.relative_to(ROOT)}")
print(f"  total line items:  {total_items}")
print(f"  avg items/cust:    {total_items / len(customers):.1f}")
print()
print("By archetype:")
arche_counter = Counter(c["shopper_id"].rsplit("_", 1)[0] for c in customers)
for arche in ARCHETYPES:
    prefix = f"ph_{ARCHETYPES.index(arche):02d}"
    items = [c for c in customers if c["shopper_id"].startswith(prefix)]
    if items:
        items_count = sum(c["purchase_history"]["aggregates"]["total_items_purchased"] for c in items)
        print(f"  {arche['id']:<32}  n={len(items):>2}  items={items_count}")
print()
print("Top 10 customers by total_items_purchased:")
sorted_c = sorted(customers, key=lambda c: -c["purchase_history"]["aggregates"]["total_items_purchased"])
for c in sorted_c[:10]:
    agg = c["purchase_history"]["aggregates"]
    print(f"  {c['shopper_id']}  items={agg['total_items_purchased']:>3}  "
          f"last={agg['last_order_at']}  return_rate={agg['return_rate']}")
