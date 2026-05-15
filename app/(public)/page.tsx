import { getPersona } from "@/lib/personas";
import { resolveShopperId } from "@/lib/shopper";

type SearchParams = Promise<{ shopper?: string }>;

export default async function Home({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const sp = await searchParams;
  const shopperId = resolveShopperId(sp.shopper);
  const profile = getPersona(shopperId);

  return (
    <main className="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4">
      <div className="max-w-lg text-center">
        <p className="text-xs uppercase tracking-[0.15em] text-neutral-500">
          Personalized PDP demo
        </p>
        <h1 className="mt-3 text-3xl sm:text-4xl font-medium tracking-tight">
          The same product, a different page per shopper.
        </h1>
        <p className="mt-5 text-neutral-600 leading-relaxed">
          Currently viewing as{" "}
          <span className="font-medium text-neutral-900">{profile.display_name}</span>.
          Pick a different shopper at the top to switch, then choose a product to see
          their PDP.
        </p>
      </div>
    </main>
  );
}
