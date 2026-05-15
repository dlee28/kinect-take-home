"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import type { ProductSummary } from "@/lib/catalog";

interface ShopperOption {
  id: string;
  label: string;
}

interface Props {
  products: ProductSummary[];
  shopperOptions: ShopperOption[];
}

const GROUP_ORDER = ["Ladieswear", "Menswear", "Divided", "Baby/Children", "Sport"] as const;

export function GlobalNav({ products, shopperOptions }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const currentShopperId = searchParams.get("shopper") ?? "anonymous";

  const productMatch = pathname.match(/^\/product\/(.+)$/);
  const currentArticleId = productMatch?.[1] ?? "";

  // Group 600 products by index_group_name so the picker is navigable.
  const grouped: Record<string, ProductSummary[]> = {};
  for (const p of products) {
    (grouped[p.index_group_name] ??= []).push(p);
  }

  function buildHref(path: string, shopperId: string): string {
    const sp = new URLSearchParams();
    if (shopperId && shopperId !== "anonymous") sp.set("shopper", shopperId);
    const qs = sp.toString();
    return qs ? `${path}?${qs}` : path;
  }

  return (
    <header className="sticky top-0 z-20 bg-white/95 backdrop-blur border-b border-neutral-100">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 h-16 flex items-center gap-4">
        <div className="flex items-center gap-3 flex-1 justify-end min-w-0">
          <label className="flex items-center gap-2 min-w-0">
            <span className="text-xs uppercase tracking-wide text-neutral-500 hidden sm:inline">
              Product
            </span>
            <select
              value={currentArticleId}
              onChange={(e) => {
                const id = e.target.value;
                if (id) router.push(buildHref(`/product/${id}`, currentShopperId));
              }}
              aria-label="Select product"
              className="min-w-0 max-w-[16rem] sm:max-w-xs truncate bg-white border border-neutral-200 rounded px-3 py-1.5 text-sm hover:border-neutral-400 focus:outline-none focus:ring-1 focus:ring-neutral-900 transition-colors"
            >
              <option value="">Browse 600 products…</option>
              {GROUP_ORDER.map((g) =>
                grouped[g] ? (
                  <optgroup key={g} label={g}>
                    {grouped[g].map((p) => (
                      <option key={p.article_id} value={p.article_id}>
                        {p.prod_name} ({p.article_id})
                      </option>
                    ))}
                  </optgroup>
                ) : null
              )}
            </select>
          </label>

          <label className="flex items-center gap-2">
            <span className="text-xs uppercase tracking-wide text-neutral-500 hidden sm:inline">
              Viewing as
            </span>
            <select
              value={currentShopperId}
              onChange={(e) => {
                const id = e.target.value;
                // Hard reload rather than router.push so every module
                // (carousel, wishlist, hero) re-fetches from scratch.
                window.location.assign(buildHref(pathname, id));
              }}
              aria-label="Viewing as persona"
              className="bg-white border border-neutral-200 rounded px-3 py-1.5 text-sm hover:border-neutral-400 focus:outline-none focus:ring-1 focus:ring-neutral-900 transition-colors"
            >
              {shopperOptions.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>
    </header>
  );
}
