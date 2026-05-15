import Image from "next/image";
import Link from "next/link";
import { headers } from "next/headers";
import { notFound } from "next/navigation";

import { getProduct } from "@/lib/catalog";
import { getPersona } from "@/lib/personas";
import { resolveShopperId } from "@/lib/shopper";
import { ANONYMOUS_ID } from "@/lib/types/profile";
import DoumWidget from "@/app/(public)/_components/DoumWidget";
import { SizePicker } from "@/app/(public)/_components/SizePicker";
import type {
  CarouselItem,
  SelectedCustomer,
} from "@/lib/recommend/customers-like-you-bought";
import type { PopularItem } from "@/lib/recommend/popular-in-category";
import type { WishlistView } from "@/lib/recommend/wishlist";

type Params = Promise<{ article_id: string }>;
type SearchParams = Promise<{ shopper?: string }>;

type RecommendResponse =
  | {
      strategy: "customers_like_you_bought";
      items: CarouselItem[];
      selected_customers: SelectedCustomer[];
    }
  | {
      strategy: "popular_in_category";
      items: PopularItem[];
      category: { index_group_name: string; product_type_name: string };
    };

interface WishlistResponse {
  items: WishlistView[];
}

// Append ?shopper=X to internal links so the persona persists across navigation.
function withShopper(path: string, shopperId: string | undefined): string {
  if (!shopperId || shopperId === "anonymous") return path;
  return `${path}?shopper=${encodeURIComponent(shopperId)}`;
}

// Map a garment_group to the persona's declared-size field that applies.
// Mirrors lib/recommend/wishlist.ts's mapping — kept local to avoid a
// shared dep just for this one function.
function sizeFieldForGarment(
  garment: string
): "top" | "bottom" | "shoe" | undefined {
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
    ].includes(garment)
  ) {
    return "top";
  }
  if (
    ["Trousers", "Trousers Denim", "Skirts", "Shorts", "Swimwear"].includes(
      garment
    )
  ) {
    return "bottom";
  }
  if (garment === "Shoes") return "shoe";
  return undefined;
}

async function postJSON<T>(path: string, body: unknown): Promise<T | null> {
  const h = await headers();
  const host = h.get("host") ?? "localhost:3000";
  const protocol = process.env.NODE_ENV === "production" ? "https" : "http";
  try {
    const res = await fetch(`${protocol}://${host}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch (err) {
    console.error(`postJSON ${path} failed:`, err);
    return null;
  }
}

export default async function ProductPage({
  params,
  searchParams,
}: {
  params: Params;
  searchParams: SearchParams;
}) {
  const { article_id } = await params;
  const product = getProduct(article_id);
  if (!product) notFound();

  const sp = await searchParams;
  const rawShopper = sp.shopper;
  const shopperId = resolveShopperId(rawShopper);

  // For identified shoppers: "customers like you bought" + wishlist alerts.
  // For anonymous (no shopper in URL, or explicit ?shopper=anonymous): a
  // popular-in-category carousel scoped to this product's category. The
  // API switches strategies internally based on shopperId + articleId.
  const isAnonymous = shopperId === ANONYMOUS_ID;
  const [recs, wishlist] = await Promise.all([
    postJSON<RecommendResponse>("/api/recommend", {
      shopperId,
      articleId: product.article_id,
      limit: 8,
    }),
    isAnonymous
      ? Promise.resolve(null)
      : postJSON<WishlistResponse>("/api/wishlist", { shopperId }),
  ]);

  const displayPrice = product.sale_price ?? product.price_usd;
  const heroOnSale = product.sale_price !== undefined;

  // Pre-select the size dropdown to the persona's declared size for this
  // garment group, when applicable. Anonymous → undefined → "Select size".
  const profile = isAnonymous ? null : getPersona(shopperId);
  const sizeField = sizeFieldForGarment(product.garment_group_name);
  const declaredSize = sizeField
    ? profile?.declared?.sizes?.[sizeField]
    : undefined;

  return (
    <main className="min-h-screen bg-white text-neutral-900">
      <header className="border-b border-neutral-100">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-4">
          <nav aria-label="Breadcrumb" className="text-xs text-neutral-500">
            <ol className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <li>
                <Link
                  href={withShopper("/", rawShopper)}
                  className="hover:text-neutral-900 transition-colors"
                >
                  Home
                </Link>
              </li>
              <li aria-hidden className="text-neutral-300">
                /
              </li>
              <li>{product.index_group_name}</li>
              <li aria-hidden className="text-neutral-300">
                /
              </li>
              <li>{product.department_name}</li>
              <li aria-hidden className="text-neutral-300">
                /
              </li>
              <li>{product.product_group_name}</li>
              <li aria-hidden className="text-neutral-300">
                /
              </li>
              <li className="text-neutral-900">{product.product_type_name}</li>
            </ol>
          </nav>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8 lg:py-12">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-16">
          {/* Image */}
          <div className="lg:sticky lg:top-24 self-start">
            <div className="relative aspect-[3/4] w-full bg-neutral-50 rounded-md overflow-hidden">
              <Image
                src={product.image_url}
                alt={product.prod_name}
                fill
                sizes="(min-width: 1024px) 50vw, 100vw"
                className="object-cover"
                priority
              />
              {heroOnSale && (
                <span className="absolute top-3 left-3 bg-red-600 text-white text-xs font-medium px-2 py-1 rounded">
                  -{product.sale_percentage}% OFF
                </span>
              )}
            </div>
          </div>

          {/* Info */}
          <div className="flex flex-col gap-6">
            <div>
              <p className="text-xs uppercase tracking-[0.15em] text-neutral-500">
                {product.product_type_name}
              </p>
              <h1 className="mt-2 text-3xl sm:text-4xl font-medium tracking-tight">
                {product.prod_name}
              </h1>
              <p className="mt-2 text-xs text-neutral-400 tabular-nums">
                ID: {product.article_id}
              </p>
            </div>

            <div className="flex items-baseline gap-3 tabular-nums">
              <span
                className={
                  heroOnSale
                    ? "text-2xl font-medium text-red-600"
                    : "text-2xl"
                }
              >
                ${displayPrice.toFixed(2)}
              </span>
              {heroOnSale && (
                <>
                  <span className="text-base text-neutral-400 line-through">
                    ${product.price_usd.toFixed(2)}
                  </span>
                  <span className="text-xs font-medium text-red-600 bg-red-50 px-1.5 py-0.5 rounded">
                    -{product.sale_percentage}%
                  </span>
                </>
              )}
            </div>

            <SizePicker
              stockBySize={product.stock_by_size}
              declaredSize={declaredSize}
            />

            <dl className="grid grid-cols-[8rem_1fr] gap-y-3 text-sm border-t border-neutral-100 pt-6">
              <dt className="text-neutral-500">Color</dt>
              <dd>{product.colour_group_name}</dd>
              <dt className="text-neutral-500">Pattern</dt>
              <dd>{product.graphical_appearance_name}</dd>
              <dt className="text-neutral-500">Department</dt>
              <dd>{product.department_name}</dd>
              <dt className="text-neutral-500">Section</dt>
              <dd>{product.section_name}</dd>
            </dl>

            <div className="border-t border-neutral-100 pt-6">
              <h2 className="text-xs uppercase tracking-[0.15em] text-neutral-500 mb-3">
                Details
              </h2>
              <p className="text-sm text-neutral-700 leading-relaxed whitespace-pre-line">
                {product.detail_desc}
              </p>
            </div>

            <DoumWidget
              productId={product.article_id}
              userId={shopperId}
              className="min-h-[480px] w-full border-t border-neutral-100 pt-6"
            />
          </div>
        </div>

        {wishlist && wishlist.items.length > 0 && (
          <section className="mt-16 lg:mt-24 border-t border-neutral-100 pt-10">
            <h2 className="text-base font-medium uppercase tracking-[0.15em] text-neutral-900">
              From your wishlist
            </h2>

            <div className="mt-6 -mx-4 sm:mx-0 overflow-x-auto">
              <ul className="flex gap-4 px-4 sm:px-0 snap-x snap-mandatory">
                {wishlist.items.map((view) => {
                  const p = view.product;
                  const sale = view.changes.on_sale;
                  const lowStock = view.changes.low_stock_in_size;
                  return (
                    <li
                      key={p.article_id}
                      className="flex-none w-44 sm:w-56 snap-start"
                    >
                      <Link
                        href={withShopper(`/product/${p.article_id}`, rawShopper)}
                        className="group block focus:outline-none"
                      >
                        <div className="relative aspect-[3/4] bg-neutral-50 rounded-md overflow-hidden">
                          <Image
                            src={p.image_url}
                            alt={p.prod_name}
                            fill
                            sizes="(min-width: 640px) 224px, 176px"
                            className="object-cover transition-transform duration-300 group-hover:scale-[1.03]"
                          />
                          {sale && (
                            <span className="absolute top-2 left-2 bg-red-600 text-white text-[10px] font-medium px-1.5 py-0.5 rounded">
                              -{sale.sale_percentage}%
                            </span>
                          )}
                        </div>
                        <div className="mt-3">
                          <h3 className="text-sm font-medium truncate group-hover:underline">
                            {p.prod_name}
                          </h3>
                          <p className="mt-1 text-xs text-neutral-500">
                            {p.product_type_name}
                          </p>
                          <p className="mt-1 flex items-baseline gap-1.5 tabular-nums">
                            {sale ? (
                              <>
                                <span className="text-sm font-medium text-red-600">
                                  ${sale.sale_price.toFixed(2)}
                                </span>
                                <span className="text-xs text-neutral-400 line-through">
                                  ${p.price_usd.toFixed(2)}
                                </span>
                              </>
                            ) : (
                              <span className="text-sm">
                                ${p.price_usd.toFixed(2)}
                              </span>
                            )}
                          </p>
                          <div className="mt-2 flex flex-col gap-1">
                            {sale && (
                              <span className="text-[11px] text-red-600">
                                Now {sale.sale_percentage}% off since you saved it
                              </span>
                            )}
                            {lowStock && (
                              <span className="text-[11px] text-amber-700">
                                Only {lowStock.units_left} left in your size ({lowStock.size})
                              </span>
                            )}
                          </div>
                        </div>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          </section>
        )}

        {recs && recs.items.length > 0 && (
          <section className="mt-16 lg:mt-24 border-t border-neutral-100 pt-10">
            <h2 className="text-base font-medium uppercase tracking-[0.15em] text-neutral-900">
              {recs.strategy === "popular_in_category"
                ? `Popular in ${recs.category.product_type_name}`
                : "Customers like you bought"}
            </h2>

            <div className="mt-6 -mx-4 sm:mx-0 overflow-x-auto">
              <ul className="flex gap-4 px-4 sm:px-0 snap-x snap-mandatory">
                {recs.items.map((item) => (
                  <li
                    key={item.product.article_id}
                    className="flex-none w-44 sm:w-56 snap-start"
                  >
                    <Link
                      href={withShopper(`/product/${item.product.article_id}`, rawShopper)}
                      className="group block focus:outline-none"
                    >
                      <div className="relative aspect-[3/4] bg-neutral-50 rounded-md overflow-hidden">
                        <Image
                          src={item.product.image_url}
                          alt={item.product.prod_name}
                          fill
                          sizes="(min-width: 640px) 224px, 176px"
                          className="object-cover transition-transform duration-300 group-hover:scale-[1.03]"
                        />
                        {recs.strategy === "popular_in_category" && "rank" in item && (
                          <span className="absolute top-2 left-2 bg-neutral-900 text-white text-[10px] font-medium px-1.5 py-0.5 rounded tabular-nums">
                            #{item.rank}
                          </span>
                        )}
                        {recs.strategy === "popular_in_category" && "units_sold_rounded" in item && (
                          <span className="absolute top-2 right-2 bg-white/90 backdrop-blur text-neutral-800 text-[10px] font-medium px-1.5 py-0.5 rounded tabular-nums shadow-sm">
                            {item.units_sold_rounded.toLocaleString()}+ sold
                          </span>
                        )}
                      </div>
                      <div className="mt-3">
                        <h3 className="text-sm font-medium truncate group-hover:underline">
                          {item.product.prod_name}
                        </h3>
                        <p className="mt-1 text-xs text-neutral-500">
                          {item.product.product_type_name}
                        </p>
                        <p className="mt-1 text-sm tabular-nums">
                          ${item.product.price_usd.toFixed(2)}
                        </p>
                      </div>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          </section>
        )}
      </div>
    </main>
  );
}
