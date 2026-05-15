import type { Product } from "@/lib/catalog";
import { getPopularityForCategory } from "@/lib/popularity";

export interface PopularItem {
  product: Product;
  units_sold_30d: number;
  // Rounded-down "X+" bucket for display. 47 → 40, 234 → 200, 4823 → 4000.
  // The "+" suffix is added in the UI; we expose the raw rounded number.
  units_sold_rounded: number;
  rank: number;
}

function roundForDisplay(n: number): number {
  if (n < 100) return Math.floor(n / 10) * 10;
  if (n < 1000) return Math.floor(n / 100) * 100;
  return Math.floor(n / 1000) * 1000;
}

export interface PopularInCategoryResult {
  items: PopularItem[];
  category: {
    index_group_name: string;
    product_type_name: string;
  };
}

// Anonymous-visitor carousel. Given the product being viewed, return the
// best-selling items in the same (index_group, product_type) bucket from
// data/popularity_by_category.json. The current product is filtered out.
//
// Popularity is pre-sorted descending in the data file, so this is just a
// catalog lookup + slice.
export function popularInCategory(
  viewing: Product,
  catalog: Product[],
  limit = 8
): PopularInCategoryResult {
  const entries = getPopularityForCategory(
    viewing.index_group_name,
    viewing.product_type_name
  );
  const catalogById = new Map(catalog.map((p) => [p.article_id, p]));

  const items: PopularItem[] = [];
  for (const entry of entries) {
    if (entry.article_id === viewing.article_id) continue;
    const product = catalogById.get(entry.article_id);
    if (!product) continue;
    items.push({
      product,
      units_sold_30d: entry.units_sold_30d,
      units_sold_rounded: roundForDisplay(entry.units_sold_30d),
      rank: entry.rank,
    });
    if (items.length >= limit) break;
  }

  return {
    items,
    category: {
      index_group_name: viewing.index_group_name,
      product_type_name: viewing.product_type_name,
    },
  };
}
