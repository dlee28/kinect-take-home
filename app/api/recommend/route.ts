import { NextRequest } from "next/server";

import { getCatalog, getProduct } from "@/lib/catalog";
import { getPurchaseHistoryCustomers } from "@/lib/history-customers";
import { getPersona, personaIds } from "@/lib/personas";
import { ANONYMOUS_ID } from "@/lib/types/profile";
import {
  customersLikeYouBought,
  type CarouselItem,
  type SelectedCustomer,
} from "@/lib/recommend/customers-like-you-bought";
import {
  popularInCategory,
  type PopularItem,
} from "@/lib/recommend/popular-in-category";

interface RequestBody {
  shopperId?: string;
  articleId?: string;
  limit?: number;
}

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

export async function POST(req: NextRequest) {
  let body: RequestBody;
  try {
    body = (await req.json()) as RequestBody;
  } catch {
    return Response.json({ error: "invalid JSON body" }, { status: 400 });
  }

  const shopperId = body.shopperId ?? ANONYMOUS_ID;
  const limit = body.limit ?? 8;

  if (typeof shopperId !== "string" || !personaIds.includes(shopperId)) {
    return Response.json(
      { error: `unknown shopperId '${shopperId}'`, valid: personaIds },
      { status: 404 }
    );
  }
  if (typeof limit !== "number" || !Number.isFinite(limit) || limit <= 0 || limit > 10) {
    return Response.json({ error: "`limit` must be an integer in [1, 10]" }, { status: 400 });
  }

  // Anonymous + articleId → fall back to popularity-in-category. The
  // "customers like you bought" recommender has no signal to work with
  // for anonymous visitors (it returns 0-scored, gender-unfiltered
  // randomness), so popularity is a more honest cold-start surface.
  if (shopperId === ANONYMOUS_ID && body.articleId) {
    const product = getProduct(body.articleId);
    if (!product) {
      return Response.json(
        { error: `unknown articleId '${body.articleId}'` },
        { status: 404 }
      );
    }
    const result = popularInCategory(product, getCatalog(), limit);
    const response: RecommendResponse = {
      strategy: "popular_in_category",
      ...result,
    };
    return Response.json(response);
  }

  const profile = getPersona(shopperId);
  const result = customersLikeYouBought(profile, getCatalog(), getPurchaseHistoryCustomers(), { limit });
  const response: RecommendResponse = {
    strategy: "customers_like_you_bought",
    ...result,
  };
  return Response.json(response);
}
