// Shopper profile schema. Trimmed to only the fields that drive a runtime
// module — see docs/profile-schema.md for the rationale per field, and the
// audit table in the README for what each one is consumed by.

export type AgeBand = "18-24" | "25-34" | "35-44" | "45-54" | "55+";
export type GenderPresentation = "feminine" | "masculine" | "neutral";
export type Climate = "cold" | "temperate" | "hot";

export type StyleArchetype =
  | "minimalist"
  | "streetwear"
  | "classic"
  | "trend"
  | "athleisure"
  | "preppy"
  | "bohemian";

// A persona ranks the five value dimensions from 1 (most important) to 5
// (least important). All five ranks are present; none are equal — the
// vector is a strict permutation of {1,2,3,4,5}.
export type ValuePriorityRank = 1 | 2 | 3 | 4 | 5;

export interface ValuePriorities {
  price: ValuePriorityRank;
  quality: ValuePriorityRank;
  sustainability: ValuePriorityRank;
  trend: ValuePriorityRank;
  comfort: ValuePriorityRank;
}

export interface DeclaredPreferences {
  sizes: { top?: string; bottom?: string; shoe?: string };
  style_archetypes: StyleArchetype[];
  value_priorities: ValuePriorities;
  material_avoid?: Array<"wool" | "leather" | "silk" | "fur">;
}

export interface Demographics {
  age_band: AgeBand;
  gender_presentation: GenderPresentation;
  location: { climate: Climate };
}

export interface Order {
  article_ids: string[];
}

export interface PurchaseAggregates {
  // Sum of order line items. Used as the tie-breaker when selecting top-N
  // "customers like you" — we keep the most active shoppers in the pool.
  total_items_purchased?: number;
  last_order_at?: string;
  return_rate: number;
}

export interface PurchaseHistory {
  orders: Order[];
  aggregates: PurchaseAggregates;
}

// Each wishlist entry snapshots the price and stock at the moment of adding,
// so the wishlist module can fire alert badges only when state has *changed*.
export interface WishlistEntry {
  article_id: string;
  added_at: string;
  price_at_add: number;
  stock_at_add_in_my_size?: number;
}

export interface BrowseHistory {
  wishlist: WishlistEntry[];
}

export interface Affinities {
  index_groups: Record<string, number>;
  price_band: { p25: number; median: number; p75: number };
}

export interface ShopperProfile {
  shopper_id: string;
  display_name: string;

  demographics?: Demographics;
  declared?: DeclaredPreferences;
  purchase_history?: PurchaseHistory;
  browse_history?: BrowseHistory;
  segments?: string[];
  affinities?: Affinities;
}

export const ANONYMOUS_ID = "anonymous";

export function isAnonymous(p: ShopperProfile): boolean {
  return p.shopper_id === ANONYMOUS_ID;
}
