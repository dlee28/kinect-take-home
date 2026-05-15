"""Build 5 named personas + 1 anonymous visitor, persisted to data/personas.json.

Design principle
----------------
Each persona is hand-authored to **stress a different tier of the profile
schema**, so reviewers can see the PDP behave differently because of a
specific signal — not because the personas happen to differ in 30 ways at
once. See docs/profile-schema.md for tier definitions.

Persona             Dominant tier(s)               What the PDP should show differently
Ana                 Tier 3 + 7 (history)           Neutral colors, premium price band, low scarcity
Marcus              Tier 4 (browse) > Tier 3       "Based on what you viewed", trend hero, urgency
Priya               Tier 6 + cross-Tier-3          Mixed Ladies + Baby recs, no scarcity (high returner)
Diego               Tier 2 sizes + cold climate    Sport carousel, fit suggestion, performance hero
Yuki                Tier 2 declared dominates      Sustainability hero, vegan filter, Divided + cheap
Anonymous           Tier 5 only                    Cold start: similarity + UTM intent

Purchase + browse + wishlist references are drawn from the actual 600-product
catalog using simple matching rules (index_group / garment / color / price),
so every article_id resolves to a real product on the PDP.
"""

from __future__ import annotations

import json
import random
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SEED = 7
random.seed(SEED)

products = json.loads((DATA_DIR / "products.json").read_text())

def pick(predicate, k, exclude=()):
    """Pick k random article_ids matching predicate from the catalog."""
    pool = [p for p in products if predicate(p) and p["article_id"] not in exclude]
    random.shuffle(pool)
    return [p["article_id"] for p in pool[:k]]


def iso_days_ago(d: int) -> str:
    # Fixed reference date so personas are deterministic across runs.
    base = datetime(2026, 5, 12)
    return (base - timedelta(days=d)).isoformat()


def by_id(article_id: str):
    return next((p for p in products if p["article_id"] == article_id), None)


def compute_affinities(article_ids, dwell_weights=None):
    """Aggregate index_group + price_band from a list of articles.

    dwell_weights: optional dict {article_id -> weight}. Defaults to 1.0 each.
    """
    if not article_ids:
        return None
    weights = dwell_weights or {}
    idx = Counter()
    prices = []
    for aid in article_ids:
        p = by_id(aid)
        if p is None:
            continue
        w = weights.get(aid, 1.0)
        idx[p["index_group_name"]] += w
        prices.append(p["price_usd"])
    total = sum(idx.values()) or 1
    index_groups = {k: round(v / total, 3) for k, v in idx.most_common()}
    prices.sort()
    n = len(prices)
    price_band = {
        "p25": round(prices[max(0, n // 4)], 2),
        "median": round(prices[n // 2], 2),
        "p75": round(prices[min(n - 1, (3 * n) // 4)], 2),
    } if prices else {"p25": 0, "median": 0, "p75": 0}
    return {"index_groups": index_groups, "price_band": price_band}


def aggregate_orders(orders):
    """Compute the slim aggregates: total_items_purchased, last_order_at, return_rate.

    Reads `_placed_at` and `_returned_count` from the in-memory build_order
    output — those internal fields are stripped before serialization.
    """
    returns = sum(o.get("_returned_count", 0) for o in orders)
    placed = sum(len(o["article_ids"]) for o in orders)
    last = max((o["_placed_at"] for o in orders), default=None)
    return {
        "total_items_purchased": placed,
        "last_order_at": last,
        "return_rate": round(returns / placed, 2) if placed else 0,
    }


def build_order(days_ago: int, article_ids: list[str], returned: list[str] | None = None):
    """Build an in-memory order with sidecar fields used during aggregation.

    Only `article_ids` is serialized. `_placed_at` and `_returned_count` are
    stripped via `strip_internal_order_fields()` before writing the JSON.
    """
    return {
        "article_ids": article_ids,
        "_placed_at": iso_days_ago(days_ago),
        "_returned_count": len(returned or []),
    }


def strip_internal_order_fields(persona: dict) -> None:
    """Remove sidecar `_*` keys from each order before serialization."""
    ph = persona.get("purchase_history")
    if not ph:
        return
    for order in ph.get("orders", []):
        for key in list(order.keys()):
            if key.startswith("_"):
                del order[key]


# ── Persona 1: Ana ─────────────────────────────────────────────────────────
# Rich Tier 3 + 7. Ladieswear loyalist, premium band, neutral palette.
NEUTRAL_COLORS = {"Beige", "Black", "White", "Grey", "Brown"}

ana_purchases = []
# Six recent neutral, mid-premium Ladieswear orders.
seen = set()
for d in [12, 45, 78, 120, 180, 240]:
    items = pick(
        lambda p: p["index_group_name"] == "Ladieswear"
        and p["perceived_colour_master_name"] in NEUTRAL_COLORS
        and p["price_usd"] >= 30,
        k=2,
        exclude=seen,
    )
    seen.update(items)
    ana_purchases.append(build_order(d, items))
# A couple older orders, slightly broader.
for d in [310, 380]:
    items = pick(
        lambda p: p["index_group_name"] == "Ladieswear"
        and p["price_usd"] >= 25,
        k=2,
        exclude=seen,
    )
    seen.update(items)
    ana_purchases.append(build_order(d, items))
ana_browse = pick(
    lambda p: p["index_group_name"] == "Ladieswear"
    and p["perceived_colour_master_name"] in NEUTRAL_COLORS,
    k=6,
    exclude=seen,
)
ana_all = list(seen) + ana_browse
ana_dwell = {**{aid: 2.0 for aid in seen}, **{aid: 1.0 for aid in ana_browse}}

ana = {
    "shopper_id": "0001",
    "display_name": "Ana",
    "demographics": {
        "age_band": "25-34",
        "gender_presentation": "feminine",
        "location": {"climate": "temperate"},
    },
    "declared": {
        "sizes": {"top": "M", "bottom": "28", "shoe": "8"},
        "style_archetypes": ["classic", "minimalist"],
        # Ana cares most about quality and comfort. Ranks 1..5, all unique.
        "value_priorities": {
            "quality": 1, "comfort": 2, "sustainability": 3,
            "price": 4, "trend": 5,
        },
    },
    "purchase_history": {
        "orders": ana_purchases,
        "aggregates": aggregate_orders(ana_purchases),
    },
    "browse_history": {
        "wishlist": pick(
            lambda p: p["index_group_name"] == "Ladieswear"
            and p["garment_group_name"] in {"Knitwear", "Outdoor"}
            and p["price_usd"] >= 35,
            k=4,
            exclude=set(ana_all),
        ),
    },
    "segments": ["repeat_buyer", "low_returner", "newsletter_engaged"],
    "affinities": compute_affinities(ana_all, ana_dwell),
}


# ── Persona 2: Marcus ──────────────────────────────────────────────────────
# Tier 4 dominates. Heavy browse, thin purchases. Streetwear/trend, bold colors.
BOLD_COLORS = {"Black", "White", "Red", "Blue", "Yellow", "Green", "Orange"}

marcus_purchases = [
    build_order(60, pick(
        lambda p: p["index_group_name"] == "Menswear" and p["price_usd"] < 35,
        k=1, exclude=set())),
    build_order(150, pick(
        lambda p: p["index_group_name"] == "Divided" and p["price_usd"] < 30,
        k=1, exclude=set())),
    build_order(290, pick(
        lambda p: p["index_group_name"] == "Menswear",
        k=2, exclude=set())),
]
marcus_purchased = {aid for o in marcus_purchases for aid in o["article_ids"]}
# Heavy recent browse — many articles, long dwell, last 14 days.
marcus_browse = pick(
    lambda p: p["index_group_name"] in {"Menswear", "Divided"}
    and p["perceived_colour_master_name"] in BOLD_COLORS
    and p["garment_group_name"] in {"Jersey Fancy", "Jersey Basic", "Trousers Denim",
                                     "Shirts", "Outdoor", "Shoes", "Knitwear"},
    k=18,
    exclude=marcus_purchased,
)
marcus_dwell = {**{aid: 80.0 for aid in marcus_browse[:6]}, **{aid: 30.0 for aid in marcus_browse[6:]}}
marcus_dwell.update({aid: 1.0 for aid in marcus_purchased})

marcus = {
    "shopper_id": "0002",
    "display_name": "Marcus",
    "demographics": {
        "age_band": "18-24",
        "gender_presentation": "masculine",
        "location": {"climate": "temperate"},
    },
    "declared": {
        "sizes": {"top": "L", "bottom": "32", "shoe": "10"},
        "style_archetypes": ["streetwear", "trend"],
        # Marcus is trend-led and price-conscious; quality and sustainability barely register.
        "value_priorities": {
            "trend": 1, "price": 2, "comfort": 3,
            "quality": 4, "sustainability": 5,
        },
    },
    "purchase_history": {
        "orders": marcus_purchases,
        "aggregates": aggregate_orders(marcus_purchases),
    },
    "browse_history": {
        # Marcus has no wishlist — demonstrates that a persona without
        # wishlist data simply doesn't surface the wishlist module,
        # which is the honest behavior.
        "wishlist": [],
    },
    "segments": ["browse_heavy", "low_purchase_intent_q1", "social_referral"],
    "affinities": compute_affinities(list(marcus_purchased) + marcus_browse, marcus_dwell),
}


# ── Persona 3: Priya ───────────────────────────────────────────────────────
# Tier 6 segments + cross-category Tier 3. New parent, high returner, hot climate.
priya_purchases = []
# Recent: Baby/Children heavy.
for d in [8, 22, 38, 55]:
    items = pick(
        lambda p: p["index_group_name"] == "Baby/Children",
        k=2, exclude={x for o in priya_purchases for x in o["article_ids"]},
    )
    # A third of items get returned (high returner).
    returned = [items[0]] if random.random() < 0.5 else None
    priya_purchases.append(build_order(d, items, returned))
# Older: Ladieswear, athleisure-ish, hot-climate appropriate.
for d in [180, 260]:
    items = pick(
        lambda p: p["index_group_name"] == "Ladieswear"
        and p["garment_group_name"] not in {"Knitwear", "Outdoor"}
        and p["perceived_colour_master_name"] != "wool",
        k=2, exclude={x for o in priya_purchases for x in o["article_ids"]},
    )
    priya_purchases.append(build_order(d, items))
priya_purchased = {aid for o in priya_purchases for aid in o["article_ids"]}
priya_browse = (
    pick(lambda p: p["index_group_name"] == "Baby/Children", k=6, exclude=priya_purchased)
    + pick(lambda p: p["index_group_name"] == "Ladieswear"
           and p["garment_group_name"] not in {"Knitwear", "Outdoor"},
           k=4, exclude=priya_purchased)
)

priya = {
    "shopper_id": "0003",
    "display_name": "Priya",
    "demographics": {
        "age_band": "35-44",
        "gender_presentation": "feminine",
        "location": {"climate": "hot"},
    },
    "declared": {
        "sizes": {"top": "S", "bottom": "26", "shoe": "7"},
        "style_archetypes": ["athleisure", "minimalist"],
        # Priya is price-led (parent on a budget), then quality, then comfort.
        "value_priorities": {
            "price": 1, "quality": 2, "comfort": 3,
            "sustainability": 4, "trend": 5,
        },
        "material_avoid": ["wool"],
    },
    "purchase_history": {
        "orders": priya_purchases,
        "aggregates": aggregate_orders(priya_purchases),
    },
    "browse_history": {
        "wishlist": pick(
            lambda p: p["index_group_name"] == "Baby/Children"
            and p["garment_group_name"] in {"Shoes", "Jersey Basic"},
            k=3, exclude=priya_purchased | set(priya_browse),
        ),
    },
    "segments": ["new_parent", "returns_high", "multi_shopper_household"],
    "affinities": compute_affinities(list(priya_purchased) + priya_browse),
}


# ── Persona 4: Diego ───────────────────────────────────────────────────────
# Tier 2 sizes + cold climate. Sport-heavy, performance framing.
diego_purchases = []
for d in [20, 65, 140, 220, 310]:
    items = pick(
        lambda p: p["index_group_name"] in {"Sport", "Menswear"}
        and (p["garment_group_name"] in {"Jersey Fancy", "Jersey Basic", "Outdoor",
                                          "Shoes", "Trousers", "Knitwear"}),
        k=2, exclude={x for o in diego_purchases for x in o["article_ids"]},
    )
    diego_purchases.append(build_order(d, items))
diego_purchased = {aid for o in diego_purchases for aid in o["article_ids"]}
diego_browse = pick(
    lambda p: p["index_group_name"] in {"Sport", "Menswear"}
    and p["garment_group_name"] in {"Outdoor", "Knitwear", "Shoes", "Trousers"},
    k=12, exclude=diego_purchased,
)

diego = {
    "shopper_id": "0004",
    "display_name": "Diego",
    "demographics": {
        "age_band": "35-44",
        "gender_presentation": "masculine",
        "location": {"climate": "cold"},
    },
    "declared": {
        "sizes": {"top": "L", "bottom": "34", "shoe": "11"},
        "style_archetypes": ["athleisure", "classic"],
        # Diego is comfort-first (outdoor athlete), then quality.
        "value_priorities": {
            "comfort": 1, "quality": 2, "price": 3,
            "sustainability": 4, "trend": 5,
        },
    },
    "purchase_history": {
        "orders": diego_purchases,
        "aggregates": aggregate_orders(diego_purchases),
    },
    "browse_history": {
        "wishlist": pick(
            lambda p: p["index_group_name"] in {"Sport", "Menswear"}
            and p["garment_group_name"] == "Outdoor",
            k=4, exclude=diego_purchased | set(diego_browse),
        ),
    },
    "segments": ["long_tenured", "outdoor_enthusiast", "low_returner"],
    "affinities": compute_affinities(list(diego_purchased) + diego_browse),
}


# ── Persona 5: Yuki ────────────────────────────────────────────────────────
# Tier 2 declared dominates. Vegan, sustainability-led, Divided + budget band.
yuki_purchases = []
for d in [30, 110]:
    items = pick(
        lambda p: p["index_group_name"] in {"Divided", "Ladieswear"}
        and p["price_usd"] <= 30,
        k=2, exclude={x for o in yuki_purchases for x in o["article_ids"]},
    )
    yuki_purchases.append(build_order(d, items))
yuki_purchased = {aid for o in yuki_purchases for aid in o["article_ids"]}
yuki_browse = pick(
    lambda p: p["index_group_name"] in {"Divided", "Ladieswear"}
    and p["price_usd"] <= 35
    and p["garment_group_name"] not in {"Shoes"},  # avoid leather
    k=10, exclude=yuki_purchased,
)

yuki = {
    "shopper_id": "0005",
    "display_name": "Yuki",
    "demographics": {
        "age_band": "18-24",
        "gender_presentation": "feminine",
        "location": {"climate": "temperate"},
    },
    "declared": {
        "sizes": {"top": "XS", "bottom": "24", "shoe": "6"},
        "style_archetypes": ["minimalist", "bohemian"],
        # Yuki is sustainability-led, then price (gen-z budget).
        "value_priorities": {
            "sustainability": 1, "price": 2, "quality": 3,
            "comfort": 4, "trend": 5,
        },
        "material_avoid": ["wool", "leather", "silk", "fur"],
    },
    "purchase_history": {
        "orders": yuki_purchases,
        "aggregates": aggregate_orders(yuki_purchases),
    },
    "browse_history": {
        "wishlist": pick(
            lambda p: p["index_group_name"] == "Divided"
            and p["price_usd"] <= 25,
            k=4, exclude=yuki_purchased | set(yuki_browse),
        ),
    },
    "segments": ["values_led", "first_year_customer", "gen_z"],
    "affinities": compute_affinities(list(yuki_purchased) + yuki_browse),
}


# ── Anonymous visitor (sentinel) ──────────────────────────────────────────
# Anonymous keeps the string id "anonymous" since that's how lib/shopper.ts
# distinguishes "no shopper" from "real shopper" throughout the app.
anonymous = {
    "shopper_id": "anonymous",
    "display_name": "Visitor",
}


personas = [ana, marcus, priya, diego, yuki, anonymous]

# Strip the sidecar `_placed_at` / `_returned_count` fields that
# aggregate_orders used internally — they should not be serialized.
for persona in personas:
    strip_internal_order_fields(persona)

(DATA_DIR / "personas.json").write_text(json.dumps(personas, indent=2))

print(f"Wrote {len(personas)} personas to data/personas.json")
print()
for p in personas:
    aff = p.get("affinities")
    purch = p.get("purchase_history", {}).get("aggregates", {})
    print(f"── {p['display_name']:<10} ({p['shopper_id']})")
    if "demographics" in p:
        d = p["demographics"]
        print(f"   {d['age_band']} {d['gender_presentation']:<9} "
              f"climate={d['location']['climate']}")
    if purch:
        print(f"   {purch.get('total_items_purchased', 0)} items  "
              f"last_order_at={purch.get('last_order_at')}  "
              f"return_rate={purch.get('return_rate', 0)}")
    if aff:
        top_idx = list(aff["index_groups"].items())[:3]
        print(f"   top index_groups: {top_idx}")
        print(f"   price_band:       {aff['price_band']}")
    print(f"   segments:         {p.get('segments', [])}")
    print()
