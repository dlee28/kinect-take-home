"""Add a `reviews` field to each persona in purchase_history_personas.json.

Reviews live at: persona["reviews"][article_id] = {rating, title, text, submitted_at}
Only a subset of personas write reviews, and reviewers only review a subset
of their purchased items. Review tone/content varies by persona archetype,
return-rate, value priorities, and product attributes (type, color, fabric).

Deterministic via SEED so re-running produces the same data.
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SEED = 42
random.seed(SEED)

products = json.loads((DATA_DIR / "products.json").read_text())
products_by_id = {p["article_id"]: p for p in products}

personas = json.loads((DATA_DIR / "purchase_history_personas.json").read_text())


# ── Phrase pools, by axis ────────────────────────────────────────────────
QUALITY_POS = [
    "Fabric feels substantial and well-made",
    "Stitching is clean and the seams have held up after several washes",
    "Quality is exactly what I'd expect at this price point",
    "Material is heavier and softer than I expected",
    "Construction feels solid — no loose threads, hems are even",
]
QUALITY_MIX = [
    "Construction is decent but a stray thread or two",
    "Quality feels mid-range — fine for the price, not a wow factor",
    "Held up okay but I'd hand-wash to be safe",
]
QUALITY_NEG = [
    "Fabric pilled after the second wash",
    "Started losing shape pretty quickly",
    "Felt thinner in person than I expected",
]

FIT_POS = [
    "fits true to size",
    "the cut is flattering without being tight",
    "drape is exactly right",
    "sits well on the shoulders",
    "length hits in a really wearable spot",
]
FIT_MIX = [
    "runs slightly small — size up if you're between sizes",
    "the fit is a bit boxy through the middle",
    "length is a touch shorter than I'd prefer",
]
FIT_NEG = [
    "sizing is off — had to return for a different size",
    "the cut just didn't work on my frame",
]

COLOR_POS_TMPL = [
    "The {color} is true to the photos",
    "Color is rich and exactly what I wanted",
    "{color} pairs with everything in my closet",
]
COLOR_MIX_TMPL = [
    "The {color} is a touch lighter in person than online",
    "Color is fine but not as saturated as the photo suggests",
]

VALUE_POS = [
    "Genuinely a great value",
    "For the price, hard to beat",
    "Worth every dollar",
]
VALUE_MIX = [
    "Reasonable for the price",
    "Fair value but I wouldn't pay more for it",
]

OPENERS_POS = [
    "Really happy with this.",
    "Bought after going back and forth and zero regrets.",
    "This has become a staple already.",
    "Picked this up on a whim and ended up loving it.",
    "Reach for this constantly.",
]
OPENERS_MIX = [
    "Bit of a mixed bag for me.",
    "Wanted to love this, settled on liking it.",
    "Decent piece, with a few caveats.",
]
OPENERS_NEG = [
    "Wanted this to work but it didn't.",
    "Returned, unfortunately.",
    "Not what I was hoping for.",
]

CLOSERS_POS = [
    "Would buy again.",
    "Already eyeing it in another color.",
    "Five stars, no notes.",
    "Highly recommend.",
]
CLOSERS_MIX = [
    "Glad I have it but probably wouldn't repurchase.",
    "Fine addition to the rotation.",
    "Take the sizing notes seriously.",
]
CLOSERS_NEG = [
    "Returning for a refund.",
    "Wouldn't recommend at full price.",
]

TITLES_POS = [
    "Exceeded expectations",
    "New favorite",
    "Better in person",
    "Nailed it",
    "Wardrobe staple",
    "Quietly excellent",
]
TITLES_MIX = [
    "Good, not great",
    "Mostly works",
    "Solid with caveats",
]
TITLES_NEG = [
    "Didn't work for me",
    "Returned",
    "Not as pictured",
]

# Archetype-flavored asides — sprinkled in occasionally.
ARCHETYPE_ASIDES = {
    "classic": [
        "Has that timeless feel I'm always after.",
        "Pairs cleanly with everything else I own.",
    ],
    "minimalist": [
        "Clean lines, no unnecessary detailing.",
        "Exactly the kind of quiet piece I keep coming back to.",
    ],
    "trendy": [
        "Hits the current vibe perfectly.",
        "Got compliments the first time I wore it.",
    ],
    "edgy": [
        "Has the right amount of attitude.",
        "Sharper in person than the photo lets on.",
    ],
    "sporty": [
        "Comfortable enough to actually move in.",
        "Great for the gym-to-coffee handoff.",
    ],
    "bohemian": [
        "Effortless drape, very my vibe.",
        "Throws on easily and looks intentional.",
    ],
    "preppy": [
        "Polished without trying too hard.",
        "Works for the office and weekends.",
    ],
    "streetwear": [
        "Fits the rotation perfectly.",
        "Looks better dressed down than I expected.",
    ],
    "romantic": [
        "Has a soft, feminine feel without being fussy.",
        "Makes me feel put-together instantly.",
    ],
    "athleisure": [
        "Comfort-first without looking sloppy.",
    ],
    "casual": [
        "Easy to throw on, easy to wear.",
    ],
    "comfort_first": [
        "Comfort is unreal — I'd live in this.",
    ],
}

# Value-priority flavor.
PRIORITY_FLAVOR = {
    "sustainability": [
        "Appreciate the materials choice.",
        "Feels like a piece I'll keep for years, which matters to me.",
    ],
    "price": [
        "Hard to find anything close at this price.",
        "Honestly didn't expect this much for the cost.",
    ],
    "quality": [
        "The construction details are what sold me.",
    ],
    "trend": [
        "Right on trend without feeling disposable.",
    ],
    "comfort": [
        "Comfortable from the first wear, no break-in.",
    ],
}


def pick(pool):
    return random.choice(pool)


def maybe(pool, p):
    return pick(pool) if random.random() < p else None


def normalize_color(p):
    c = (p.get("colour_group_name") or p.get("perceived_colour_master_name") or "").strip()
    if not c or c.lower() in {"other", "undefined", "unknown"}:
        return None
    return c.lower()


def product_noun(p):
    # Prefer the most-specific human label.
    return (p.get("product_type_name") or p.get("garment_group_name") or "piece").lower()


def review_text_for(persona, product, sentiment):
    color = normalize_color(product)
    archetypes = persona["declared"].get("style_archetypes") or []
    priorities = persona["declared"].get("value_priorities") or {}
    # value_priorities is a rank 1..5 dict; rank 1 = highest priority.
    top_priority = min(priorities, key=priorities.get) if priorities else None

    parts = []
    if sentiment == "pos":
        parts.append(pick(OPENERS_POS))
        parts.append(pick(QUALITY_POS) + ", and " + pick(FIT_POS) + ".")
        if color and random.random() < 0.6:
            parts.append(pick(COLOR_POS_TMPL).format(color=color) + ".")
        if random.random() < 0.45:
            parts.append(pick(VALUE_POS) + ".")
    elif sentiment == "mix":
        parts.append(pick(OPENERS_MIX))
        parts.append(pick(QUALITY_MIX) + ", and " + pick(FIT_MIX) + ".")
        if color and random.random() < 0.5:
            parts.append(pick(COLOR_MIX_TMPL).format(color=color) + ".")
        if random.random() < 0.35:
            parts.append(pick(VALUE_MIX) + ".")
    else:  # neg
        parts.append(pick(OPENERS_NEG))
        parts.append(pick(QUALITY_NEG) + ", and " + pick(FIT_NEG) + ".")

    # Archetype aside, sometimes.
    if archetypes and random.random() < 0.45:
        arch = pick(archetypes)
        if arch in ARCHETYPE_ASIDES and sentiment != "neg":
            parts.append(pick(ARCHETYPE_ASIDES[arch]))

    # Priority flavor, sometimes.
    if top_priority in PRIORITY_FLAVOR and sentiment == "pos" and random.random() < 0.35:
        parts.append(pick(PRIORITY_FLAVOR[top_priority]))

    if sentiment == "pos":
        parts.append(pick(CLOSERS_POS))
    elif sentiment == "mix":
        parts.append(pick(CLOSERS_MIX))
    else:
        parts.append(pick(CLOSERS_NEG))

    return " ".join(parts)


def title_for(sentiment, product):
    noun = product_noun(product)
    if sentiment == "pos":
        base = pick(TITLES_POS)
    elif sentiment == "mix":
        base = pick(TITLES_MIX)
    else:
        base = pick(TITLES_NEG)
    # Occasionally tag the noun on.
    if random.random() < 0.35:
        return f"{base} — great {noun}" if sentiment == "pos" else f"{base} on this {noun}"
    return base


def rating_from_sentiment(sentiment):
    if sentiment == "pos":
        return random.choices([5, 4], weights=[0.65, 0.35])[0]
    if sentiment == "mix":
        return random.choices([3, 4], weights=[0.7, 0.3])[0]
    return random.choices([1, 2], weights=[0.4, 0.6])[0]


def submitted_at_for(order_placed_at):
    placed = datetime.fromisoformat(order_placed_at)
    # Reviews land 5-30 days after the order.
    delta = timedelta(days=random.randint(5, 30))
    return (placed + delta).isoformat()


def sentiment_for(persona):
    # Negative reviews skew higher for personas with high return rates.
    rr = persona["purchase_history"]["aggregates"].get("return_rate", 0.2)
    p_neg = min(0.18, 0.05 + rr * 0.25)
    p_mix = 0.18
    r = random.random()
    if r < p_neg:
        return "neg"
    if r < p_neg + p_mix:
        return "mix"
    return "pos"


# ── Main ─────────────────────────────────────────────────────────────────
WRITES_REVIEWS_RATE = 0.68  # ~68% of personas have written at least one review


def reviewable_items(persona):
    """List of (article_id, base_date) for each unique purchased product.

    Orders no longer carry per-order placed_at (slimmed schema), so we use
    the persona's aggregates.last_order_at as the common base date — every
    review's submitted_at is then derived as (base + 5-30 random days).
    """
    aggregates = persona["purchase_history"].get("aggregates", {})
    base_date = aggregates.get("last_order_at")
    if not base_date:
        return []
    seen = set()
    out = []
    for o in persona["purchase_history"]["orders"]:
        for aid in o["article_ids"]:
            if aid in seen or aid not in products_by_id:
                continue
            seen.add(aid)
            out.append((aid, base_date))
    return out


total_personas_with_reviews = 0
total_reviews = 0

for persona in personas:
    persona["reviews"] = {}
    if random.random() > WRITES_REVIEWS_RATE:
        continue

    items = reviewable_items(persona)
    if not items:
        continue

    # How many reviews this persona writes: ~15-40% of distinct purchases,
    # capped at 8, with at least 1.
    target = max(1, min(8, round(len(items) * random.uniform(0.15, 0.40))))
    # Slightly favor more-recent items: weight by inverse rank.
    weights = [1.0 / (i + 1) for i in range(len(items))]
    chosen_idx = set()
    while len(chosen_idx) < target and len(chosen_idx) < len(items):
        # weighted sample without replacement, manually
        pool = [(i, w) for i, w in enumerate(weights) if i not in chosen_idx]
        total = sum(w for _, w in pool)
        r = random.random() * total
        acc = 0
        for i, w in pool:
            acc += w
            if r <= acc:
                chosen_idx.add(i)
                break

    for idx in sorted(chosen_idx):
        aid, placed_at = items[idx]
        product = products_by_id[aid]
        sentiment = sentiment_for(persona)
        persona["reviews"][aid] = {
            "rating": rating_from_sentiment(sentiment),
            "title": title_for(sentiment, product),
            "text": review_text_for(persona, product, sentiment),
            "submitted_at": submitted_at_for(placed_at),
        }
        total_reviews += 1

    if persona["reviews"]:
        total_personas_with_reviews += 1


out_path = DATA_DIR / "purchase_history_personas.json"
out_path.write_text(json.dumps(personas, indent=2))

print(
    f"Wrote {total_reviews} reviews across {total_personas_with_reviews}/"
    f"{len(personas)} personas → {out_path.relative_to(ROOT)}"
)
