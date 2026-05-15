# Shopper profile schema

This doc defines the shape of a shopper record consumed by the PDP. The
schema is the **signal model** for personalization — every field exists
because at least one PDP module reads it, and every module that needs a
signal can name the field it pulls from.

We deliberately keep the schema close in shape and field names to what a
real Shopify storefront would already have via its first-party data stack
(Customer + Order objects), its session pixel, and the apps a typical
Shopify Plus merchant stitches in (Klaviyo, a quiz app, a loyalty app, a
wishlist app). The goal is "the shape a real Shopify app would actually
have" — not the most expressive imaginable schema.

## Where each signal comes from on a real Shopify store

| Tier                       | Source on a real Shopify store                                                                                  | Latency       |
| -------------------------- | --------------------------------------------------------------------------------------------------------------- | ------------- |
| Identity                   | Shopify Customer object (id, email, account creation, marketing consent)                                        | persistent    |
| Demographics + declared    | Account signup form, post-purchase survey, style quiz apps (Octane AI, Shop Quiz), Klaviyo profile properties   | persistent    |
| Purchase history           | Shopify Orders API + returns from the Refunds API                                                               | persistent    |
| Browsing + engagement      | Shopify Web Pixel / GA4 / Klaviyo onsite tracking; identifies via Klaviyo `_kx` cookie or signed-in customer    | minutes       |
| Session                    | Current request: device UA, geoIP, referrer + UTM, Shopify cart cookie, time-of-day                             | real-time     |
| Loyalty + segments         | Shopify customer `tags`, Shopify Plus Audiences, loyalty app (Smile.io / Yotpo), Klaviyo segments               | hourly/daily  |
| Inferred affinities        | Derived offline from purchase + browse history (category/color/price band)                                      | nightly batch |

## Tiers in detail

### 1. Identity

```ts
shopper_id: string         // Shopify customer.id
display_name: string       // First name, used for hero copy ("Welcome back, Ana")
account_created_at: string // ISO date
```

Every personalization module needs an ID to join on. `display_name` is the
only personal data shown in the UI. `account_created_at` lets us bucket
"new" vs "tenured" shoppers (tenured shoppers tolerate less generic copy).

### 2. Demographics + declared preferences

```ts
demographics: {
  age_band: '18-24' | '25-34' | '35-44' | '45-54' | '55+'
  gender_presentation: 'feminine' | 'masculine' | 'neutral'
  location: { city: string; country: string; climate: 'cold' | 'temperate' | 'hot' }
}

declared: {
  sizes: { top?: string; bottom?: string; shoe?: string }
  style_archetypes: Array<'minimalist'|'streetwear'|'classic'|'trend'|'athleisure'|'preppy'|'bohemian'>
  value_priorities: {           // weights sum to 1
    price: number               // budget-driven
    quality: number             // longevity / craftsmanship
    sustainability: number      // materials, ethics
    trend: number               // newness, look
    comfort: number             // fit, fabric feel
  }
  material_avoid?: Array<'wool'|'leather'|'silk'|'fur'> // vegan / allergy signal
}
```

**Why these fields:**

- `gender_presentation` (not biological sex) gates the `index_group` filter
  cheaply and respectfully — it's the single biggest catalog narrower.
- `climate` flips the seasonal slice. A Phoenix shopper sees less knitwear
  than a Minneapolis shopper, even for the same query.
- `style_archetypes` (max 3) is what almost every style quiz returns. We
  use it for the hero copy framing and as a re-ranker on the carousel.
- `value_priorities` is a small weight vector, not a free-text "what do
  you care about" — it lets the **hero copy module** swap headline framing
  (price vs. sustainability vs. trend) without a model call. This is the
  single most under-used signal on real Shopify stores.
- `sizes` powers the **fit suggestion module**. A real store gets this
  from a fit quiz, a returns reason, or an explicit account preference.
- `material_avoid` is the cheap, high-value flag most stores skip. One
  vegan customer seeing leather hero copy ruins the rest of the session.

### 3. Purchase history

```ts
purchase_history: {
  orders: Array<{
    order_id: string
    article_ids: string[]   // products in the line items
    placed_at: string
    total_usd: number
    returned_article_ids?: string[]
  }>
  aggregates: {
    total_orders: number
    lifetime_value_usd: number
    avg_order_value_usd: number
    last_order_at?: string
    return_rate: number     // 0..1, computed
  }
}
```

This is the highest-signal tier. We store both the raw orders (so the
"customers like you bought" module can join across shoppers) and the
pre-computed aggregates (so we never recompute LTV on a page render).

`return_rate` is included because it changes the urgency module: a high
returner shouldn't see "selling fast — only 3 left" copy that pushes a
likely-return purchase.

### 4. Browsing + session-derived engagement

```ts
browse_history: {
  recent_views: Array<{ article_id: string; viewed_at: string; dwell_seconds: number }>
  recent_searches: string[]
  wishlist: string[]   // article_ids
}
```

We keep dwell-time because it's the only browsing signal that disambiguates
"I bounced after 2 seconds" from "I read every spec." Real stores
get this from the Klaviyo / GA4 pixel and from Shopify's Web Pixel API.

### 5. Session context (live, request-scoped)

```ts
session: {
  device: 'mobile' | 'desktop' | 'tablet'
  traffic_source: 'organic' | 'paid_search' | 'paid_social' | 'email' | 'direct' | 'referral'
  utm?: { campaign?: string; content?: string }  // ad creative -> infer category interest
  referrer_query?: string                         // search engine query (kept if available)
  time_of_day: 'morning' | 'midday' | 'evening' | 'late_night'
  day_of_week: 'weekday' | 'weekend'
  current_cart: string[]                          // article_ids
}
```

Session signals are the **only** signals an anonymous visitor has. They
also matter for known shoppers: a known shopper arriving from a "summer
dresses" email should not see a "winter coats" carousel even if their
all-time history skews that way.

`utm.campaign` is a deliberate inclusion — it's the closest thing to a
declared intent for a fresh visitor. If they clicked an ad for
"linen shirts", that's almost a query.

### 6. Loyalty + segments

```ts
loyalty: {
  tier: 'none' | 'silver' | 'gold' | 'vip'
  points: number
}
segments: string[]   // free-form, e.g. 'vip', 'new_parent', 'returns_high'
```

Tier gates exclusive-feeling copy ("VIP early access"). `segments` is a
free-form bag because every Shopify store ends up with idiosyncratic
customer tags that drive merchandising rules — we mirror that.

### 7. Inferred affinities (derived nightly)

```ts
affinities: {
  index_groups: Record<string, number>      // e.g. { Ladieswear: 0.7, Sport: 0.3 }
  garment_groups: Record<string, number>
  colors: Record<string, number>            // perceived_colour_master_name keys
  price_band: { p25: number; median: number; p75: number }
}
```

Derived from purchase + dwell-weighted browse. Storing these explicitly
keeps the PDP request fast (no scans across order history per render) and
gives us a clean knob to test against (we can swap derivation strategies
without changing the consumer code). On a real Shopify store this lives
in a `customer_metafield` namespace or a Klaviyo predictive property.

## Anonymous visitor

The anonymous record has **only Tier 5** populated. Concretely it looks
like:

```ts
{
  shopper_id: 'anonymous',
  display_name: 'Visitor',
  session: { device, traffic_source, utm, time_of_day, day_of_week, current_cart: [] },
  // everything else: undefined
}
```

Every module must handle missing fields. The cold-start strategy is
documented separately (see `docs/cold-start.md` when written) but at the
schema level the rule is: undefined ≠ empty, and modules degrade by
falling back to content similarity from the **current PDP product** plus
whatever session signal exists.

## What we intentionally left out

These would belong on a real store but don't drive any module we're
shipping, so including them would just inflate the schema:

- Email open / click rates per campaign (only useful for re-engagement, not PDP)
- Subscription state (Recharge etc.) — relevant for replenishment, not fashion
- Shipping address book (relevant for checkout, not PDP)
- Wishlist sharing, gift-list metadata
- Predicted next-order date / churn probability

If we add a "you'll need this again soon" module these come back in.
