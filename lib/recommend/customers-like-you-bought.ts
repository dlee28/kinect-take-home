import type { Product } from "@/lib/catalog";
import {
  ANONYMOUS_ID,
  type ShopperProfile,
  type ValuePriorities,
} from "@/lib/types/profile";

export interface CarouselItem {
  product: Product;
  bought_by_count: number;
}

export interface SelectedCustomer {
  shopper_id: string;
  match_score: number;
}

export interface RecommendResult {
  items: CarouselItem[];
  selected_customers: SelectedCustomer[];
}

export interface RecommendOptions {
  limit?: number;
}

// ── Helpers ─────────────────────────────────────────────────────────────

function topNKeys(record: Record<string, number> | undefined, n: number): string[] {
  if (!record) return [];
  return Object.entries(record)
    .sort(([, a], [, b]) => b - a)
    .slice(0, n)
    .map(([k]) => k);
}

function priceBandsOverlap(a: ShopperProfile, b: ShopperProfile): boolean {
  const ap = a.affinities?.price_band;
  const bp = b.affinities?.price_band;
  if (!ap || !bp) return false;
  return ap.p25 <= bp.p75 && bp.p25 <= ap.p75;
}

// Return the field names of the top-N ranked value priorities (rank 1
// = highest). value_priorities is a rank-1-to-5 dict where each value is
// a unique integer 1..5.
function topRankedValueKeys(
  priorities: ValuePriorities | undefined,
  n: number
): string[] {
  if (!priorities) return [];
  return (Object.entries(priorities) as [string, number][])
    .filter(([, rank]) => rank <= n)
    .map(([k]) => k);
}

// "Now" is inferred from the data so we don't need to hardcode a date
// that has to be kept in sync with the persona generators.
function inferNow(history: ShopperProfile[]): number {
  let maxTs = 0;
  for (const c of history) {
    const last = c.purchase_history?.aggregates?.last_order_at;
    if (last) {
      const t = Date.parse(last);
      if (t > maxTs) maxTs = t;
    }
  }
  return maxTs;
}

// Soft score per history customer. Higher = better lookalike.
//   +2    age_band exact match
//   +1    per shared style_archetype
//   +2    top index_group in current's top-2
//   +2    price_band ranges overlap
//   +1    per shared field in current's top-2 value_priorities ranks (max +2)
//   +1    per shared segment
//   +1    last_order_at within 30 days
//   +0.5  climate exact match
//   -2    return_rate > 0.3
function scoreHistoryCustomer(
  current: ShopperProfile,
  hist: ShopperProfile,
  nowMs: number
): number {
  let s = 0;

  if (current.demographics?.age_band === hist.demographics?.age_band) s += 2;

  const curStyles = new Set(current.declared?.style_archetypes ?? []);
  for (const st of hist.declared?.style_archetypes ?? []) {
    if (curStyles.has(st)) s += 1;
  }

  const curTopIdx = topNKeys(current.affinities?.index_groups, 2);
  const histTop = topNKeys(hist.affinities?.index_groups, 1)[0];
  if (histTop && curTopIdx.includes(histTop)) s += 2;

  if (priceBandsOverlap(current, hist)) s += 2;

  const curTopValues = topRankedValueKeys(current.declared?.value_priorities, 2);
  const histTopValues = new Set(
    topRankedValueKeys(hist.declared?.value_priorities, 2)
  );
  for (const k of curTopValues) {
    if (histTopValues.has(k)) s += 1;
  }

  const curSegs = new Set(current.segments ?? []);
  for (const seg of hist.segments ?? []) {
    if (curSegs.has(seg)) s += 1;
  }

  const last = hist.purchase_history?.aggregates?.last_order_at;
  if (last) {
    const days = (nowMs - Date.parse(last)) / (1000 * 60 * 60 * 24);
    if (days >= 0 && days <= 30) s += 1;
  }

  if (
    current.demographics?.location.climate ===
    hist.demographics?.location.climate
  ) {
    s += 0.5;
  }

  if ((hist.purchase_history?.aggregates?.return_rate ?? 0) > 0.3) s -= 2;

  return s;
}

export function customersLikeYouBought(
  currentProfile: ShopperProfile,
  catalog: Product[],
  historyCustomers: ShopperProfile[],
  opts: RecommendOptions = {}
): RecommendResult {
  const limit = opts.limit ?? 8;
  const isAnonymous = currentProfile.shopper_id === ANONYMOUS_ID;
  const catalogById = new Map(catalog.map((p) => [p.article_id, p]));

  // ── Hard floor: exact gender_presentation (skip for anonymous) ─────────
  const survivors = isAnonymous
    ? historyCustomers
    : historyCustomers.filter(
        (c) =>
          c.demographics?.gender_presentation ===
          currentProfile.demographics?.gender_presentation
      );

  // ── Soft score each surviving customer ─────────────────────────────────
  const nowMs = inferNow(historyCustomers);
  const scored = survivors.map((c) => ({
    customer: c,
    score: isAnonymous ? 0 : scoreHistoryCustomer(currentProfile, c, nowMs),
  }));

  // Sort by score desc, then total_items_purchased desc as tiebreaker.
  scored.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    const ai = a.customer.purchase_history?.aggregates?.total_items_purchased ?? 0;
    const bi = b.customer.purchase_history?.aggregates?.total_items_purchased ?? 0;
    return bi - ai;
  });
  const selected = scored.slice(0, 5);

  // ── Pool: count how many of the selected bought each product ───────────
  const freq = new Map<string, number>();
  for (const { customer } of selected) {
    const seen = new Set<string>();
    for (const order of customer.purchase_history?.orders ?? []) {
      for (const aid of order.article_ids) {
        if (seen.has(aid)) continue;
        seen.add(aid);
        freq.set(aid, (freq.get(aid) ?? 0) + 1);
      }
    }
  }

  // ── Drop owned, build items, sort by freq, slice to limit ──────────────
  const ownedIds = new Set<string>();
  for (const order of currentProfile.purchase_history?.orders ?? []) {
    for (const aid of order.article_ids) ownedIds.add(aid);
  }

  const items: CarouselItem[] = [...freq.entries()]
    .sort(([, a], [, b]) => b - a)
    .map(([aid, count]) => {
      if (ownedIds.has(aid)) return null;
      const product = catalogById.get(aid);
      return product ? { product, bought_by_count: count } : null;
    })
    .filter((x): x is CarouselItem => x !== null)
    .slice(0, limit);

  return {
    items,
    selected_customers: selected.map((s) => ({
      shopper_id: s.customer.shopper_id,
      match_score: s.score,
    })),
  };
}
