import { Suspense } from "react";

import { getProductSummaries } from "@/lib/catalog";
import { personas } from "@/lib/personas";

import { GlobalNav } from "./_components/GlobalNav";

export default function PublicLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const products = getProductSummaries();
  const shopperOptions = personas.map((p) => ({
    id: p.shopper_id,
    label: p.display_name,
  }));

  // GlobalNav uses useSearchParams(), which requires a Suspense boundary in
  // App Router. The fallback reserves header height so layout doesn't shift.
  return (
    <>
      <Suspense fallback={<div className="h-16 border-b border-neutral-100" />}>
        <GlobalNav products={products} shopperOptions={shopperOptions} />
      </Suspense>
      {children}
    </>
  );
}
