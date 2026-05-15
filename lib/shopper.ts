import { personaIds } from "@/lib/personas";

export const DEFAULT_SHOPPER_ID = "anonymous";

// Pure helper: takes whatever came in on ?shopper=... (string | undefined |
// string[] thanks to Next's loose typing for repeated params) and returns a
// guaranteed-valid persona id. Used by every page that consumes the shopper
// from its `searchParams` prop.
export function resolveShopperId(
  value: string | string[] | undefined | null
): string {
  const v = Array.isArray(value) ? value[0] : value;
  return v && personaIds.includes(v) ? v : DEFAULT_SHOPPER_ID;
}
