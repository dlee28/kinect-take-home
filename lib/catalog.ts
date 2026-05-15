import productsData from "@/data/products.json";

// Product shape mirrors the columns kept by scripts/sample_catalog.py.
// We keep it manually typed (rather than `typeof productsData[number]`)
// so consumers get explicit types and the JSON shape is documented here.
export interface Product {
  article_id: string;
  product_code: string;
  prod_name: string;
  product_type_name: string;
  product_group_name: string;
  garment_group_name: string;
  graphical_appearance_name: string;
  colour_group_name: string;
  perceived_colour_value_name: string;
  perceived_colour_master_name: string;
  department_name: string;
  index_name: string;
  index_group_name: string;
  section_name: string;
  detail_desc: string;
  image_url: string;
  // List price (never changes after sampling). Display price is
  // `sale_price ?? price_usd`.
  price_usd: number;
  sale_price?: number;
  sale_percentage?: number;
  // Units in stock per size. Sizes vary by garment_group_name; see
  // scripts/enrich_for_alerts.py for the mapping.
  stock_by_size: Record<string, number>;
}

// `as unknown as` because TS infers each JSON entry's `stock_by_size` as a
// strict literal type (different keys per garment group), and the union
// isn't directly assignable to Record<string, number>.
const catalog = productsData as unknown as Product[];
const byId = new Map(catalog.map((p) => [p.article_id, p]));

export function getCatalog(): Product[] {
  return catalog;
}

export function getProduct(articleId: string): Product | undefined {
  return byId.get(articleId);
}

// Minimal product shape for the global nav dropdown. Shipping 600 full
// products to the client would be ~860KB; this is ~30KB and is enough to
// render the picker and navigate.
export interface ProductSummary {
  article_id: string;
  prod_name: string;
  index_group_name: string;
}

const summaries: ProductSummary[] = catalog.map((p) => ({
  article_id: p.article_id,
  prod_name: p.prod_name,
  index_group_name: p.index_group_name,
}));

export function getProductSummaries(): ProductSummary[] {
  return summaries;
}
