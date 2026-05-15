"use client";

import { useState } from "react";

interface SizePickerProps {
  stockBySize: Record<string, number>;
  /** Persona's declared size for this garment group, if known. Pre-selects
   *  the dropdown when the size has stock. */
  declaredSize?: string;
}

export function SizePicker({ stockBySize, declaredSize }: SizePickerProps) {
  const sizes = Object.keys(stockBySize);
  const isOneSize = sizes.length === 1 && sizes[0] === "ONE_SIZE";

  const initial =
    !isOneSize && declaredSize && (stockBySize[declaredSize] ?? 0) > 0
      ? declaredSize
      : "";
  const [selected, setSelected] = useState<string>(
    isOneSize ? "ONE_SIZE" : initial
  );

  const selectedStock = selected ? stockBySize[selected] ?? 0 : 0;
  const canAdd = isOneSize || (selected !== "" && selectedStock > 0);
  const lowStock =
    !isOneSize && !!selected && selectedStock > 0 && selectedStock <= 3;

  return (
    <div className="flex flex-col gap-3">
      <label className="flex flex-col gap-2">
        <span className="text-xs uppercase tracking-[0.15em] text-neutral-500">
          Size
        </span>
        <select
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
          disabled={isOneSize}
          aria-label="Size"
          className="bg-white border border-neutral-300 rounded px-3 py-3 text-sm hover:border-neutral-500 focus:outline-none focus:ring-1 focus:ring-neutral-900 transition-colors disabled:bg-neutral-50 disabled:text-neutral-500"
        >
          {!isOneSize && <option value="">Select size</option>}
          {sizes.map((sz) => {
            const stock = stockBySize[sz];
            const oos = stock === 0;
            const low = stock > 0 && stock <= 3;
            const label = sz === "ONE_SIZE" ? "One size" : sz;
            const suffix = oos
              ? " — Out of stock"
              : low
                ? ` — Only ${stock} left`
                : "";
            return (
              <option key={sz} value={sz} disabled={oos}>
                {label}
                {suffix}
              </option>
            );
          })}
        </select>
      </label>

      {lowStock && (
        <p className="text-xs text-amber-700">
          Only {selectedStock} left in size {selected} — going fast.
        </p>
      )}

      <button
        type="button"
        disabled={!canAdd}
        className="w-full bg-neutral-900 text-white text-sm tracking-wide py-4 hover:bg-neutral-800 transition-colors focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:ring-offset-2 disabled:bg-neutral-300 disabled:cursor-not-allowed"
      >
        Add to bag
      </button>
    </div>
  );
}
