import popularityData from "@/data/popularity_by_category.json";

export interface PopularityEntry {
  article_id: string;
  units_sold_30d: number;
  rank: number;
}

const popularity = popularityData as Record<string, PopularityEntry[]>;

export function categoryKey(
  indexGroupName: string,
  productTypeName: string
): string {
  return `${indexGroupName}::${productTypeName}`;
}

export function getPopularityForCategory(
  indexGroupName: string,
  productTypeName: string
): PopularityEntry[] {
  return popularity[categoryKey(indexGroupName, productTypeName)] ?? [];
}
