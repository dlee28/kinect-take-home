import { NextRequest } from "next/server";

import { getCatalog } from "@/lib/catalog";
import { getPersona, personaIds } from "@/lib/personas";
import { wishlistView } from "@/lib/recommend/wishlist";

interface RequestBody {
  shopperId?: string;
}

export async function POST(req: NextRequest) {
  let body: RequestBody;
  try {
    body = (await req.json()) as RequestBody;
  } catch {
    return Response.json({ error: "invalid JSON body" }, { status: 400 });
  }

  const shopperId = body.shopperId ?? "anonymous";
  if (typeof shopperId !== "string" || !personaIds.includes(shopperId)) {
    return Response.json(
      { error: `unknown shopperId '${shopperId}'`, valid: personaIds },
      { status: 404 }
    );
  }

  const profile = getPersona(shopperId);
  const items = wishlistView(profile, getCatalog());

  return Response.json({ items });
}
