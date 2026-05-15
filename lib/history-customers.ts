import purchaseHistoryData from "@/data/purchase_history_personas.json";
import type { ShopperProfile } from "@/lib/types/profile";

// `as unknown as` because TS infers each JSON entry as a distinct literal
// shape (each customer's affinities have different keys), and the union
// isn't directly assignable to Record<string, number>.
const purchaseHistoryCustomers = purchaseHistoryData as unknown as ShopperProfile[];

export function getPurchaseHistoryCustomers(): ShopperProfile[] {
  return purchaseHistoryCustomers;
}
