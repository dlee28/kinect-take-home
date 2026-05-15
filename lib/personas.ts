import personasData from "@/data/personas.json";
import type { ShopperProfile } from "@/lib/types/profile";

export const personas = personasData as ShopperProfile[];

export const personaIds = personas.map((p) => p.shopper_id);

export function getPersona(id: string | undefined | null): ShopperProfile {
  if (!id) return getAnonymous();
  return personas.find((p) => p.shopper_id === id) ?? getAnonymous();
}

export function getAnonymous(): ShopperProfile {
  const a = personas.find((p) => p.shopper_id === "anonymous");
  if (!a) throw new Error("Anonymous persona missing from data/personas.json");
  return a;
}
