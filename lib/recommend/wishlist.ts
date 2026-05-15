import type { Product } from "@/lib/catalog";
import type { ShopperProfile } from "@/lib/types/profile";

// What's changed for a wishlist item since the moment it was added.
// Both fields are optional — an entry can have no changes (item unchanged
// since add) and still be returned by wishlistView, just without badges.
export interface WishlistChanges {
  on_sale?: {
    sale_price: number;
    sale_percentage: number;
    price_at_add: number;
  };
  low_stock_in_size?: {
    size: string;
    units_left: number;
    stock_at_add: number;
  };
}

// The enriched display shape: one wishlist entry expanded with its full
// product plus any detected changes since adding.
export interface WishlistView {
  product: Product;
  added_at: string;
  changes: WishlistChanges;
}

// Map a garment_group to the persona's declared-size field that applies.
// Returns null for one-size groups (low-stock alert can't fire).
function sizeFieldFor(garment_group: string): "top" | "bottom" | "shoe" | null {
  if (
    [
      "Jersey Fancy",
      "Jersey Basic",
      "Blouses",
      "Knitwear",
      "Shirts",
      "Outdoor",
      "Dressed",
      "Under-, Nightwear",
      "Dresses Ladies",
      "Dresses/Skirts girls",
    ].includes(garment_group)
  ) {
    return "top";
  }
  if (
    ["Trousers", "Trousers Denim", "Skirts", "Shorts", "Swimwear"].includes(
      garment_group
    )
  ) {
    return "bottom";
  }
  if (garment_group === "Shoes") return "shoe";
  return null;
}

export function wishlistView(
  profile: ShopperProfile,
  catalog: Product[]
): WishlistView[] {
  const wishlist = profile.browse_history?.wishlist;
  if (!wishlist || wishlist.length === 0) return [];

  const byId = new Map(catalog.map((p) => [p.article_id, p]));
  const declaredSizes = profile.declared?.sizes;
  const views: WishlistView[] = [];

  for (const entry of wishlist) {
    const product = byId.get(entry.article_id);
    if (!product) continue;

    const changes: WishlistChanges = {};

    // Sale change: current display price dropped below the snapshot.
    const currentPrice = product.sale_price ?? product.price_usd;
    if (
      product.sale_price !== undefined &&
      product.sale_percentage !== undefined &&
      currentPrice < entry.price_at_add
    ) {
      changes.on_sale = {
        sale_price: product.sale_price,
        sale_percentage: product.sale_percentage,
        price_at_add: entry.price_at_add,
      };
    }

    // Low-stock change: current stock in declared size is 1-5 AND lower
    // than the snapshot taken at add-time.
    const field = sizeFieldFor(product.garment_group_name);
    const declaredSize = field ? declaredSizes?.[field] : undefined;
    const snapshot = entry.stock_at_add_in_my_size;
    if (declaredSize !== undefined && snapshot !== undefined) {
      const currentStock = product.stock_by_size[declaredSize];
      if (
        typeof currentStock === "number" &&
        currentStock >= 1 &&
        currentStock <= 5 &&
        currentStock < snapshot
      ) {
        changes.low_stock_in_size = {
          size: declaredSize,
          units_left: currentStock,
          stock_at_add: snapshot,
        };
      }
    }

    // Always include the wishlist item; `changes` may be empty if the item
    // has not changed since being added. Changed items sort to the top via
    // the tier function below.
    views.push({
      product,
      added_at: entry.added_at,
      changes,
    });
  }

  // Sort tiers: both changes > sale only > low-stock only > no changes.
  // Within changed tiers, tiebreak by sale_percentage desc then prod_name.
  // Within the no-changes tier, sort by added_at desc (most recent first).
  function tier(v: WishlistView): number {
    const hasSale = !!v.changes.on_sale;
    const hasLow = !!v.changes.low_stock_in_size;
    if (hasSale && hasLow) return 0;
    if (hasSale) return 1;
    if (hasLow) return 2;
    return 3;
  }
  views.sort((a, b) => {
    const ta = tier(a);
    const tb = tier(b);
    if (ta !== tb) return ta - tb;
    if (ta < 3) {
      const pa = a.changes.on_sale?.sale_percentage ?? 0;
      const pb = b.changes.on_sale?.sale_percentage ?? 0;
      if (pa !== pb) return pb - pa;
      return a.product.prod_name.localeCompare(b.product.prod_name);
    }
    return b.added_at.localeCompare(a.added_at);
  });

  return views;
}
