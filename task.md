# Take-Home: Personalized Product Detail Page

> 💡 **For candidates:** This is a an exercise that mirrors Kinect's actual product wedge — personalizing the highest-leverage page on a Shopify site. We've scoped it deliberately small (a focused weekend), but expect it to test more design judgment than the average take-home.

## The brief

A shopper navigates to a product detail page (PDP). Build that PDP experience for them — recommendation carousels, hero copy, surfaced reviews, fit/sizing cues, whatever else you think belongs there — such that **the same product feels meaningfully different to different shoppers.**

If two different people land on the same PDP, what they see should differ in ways that are defensible, not random. That's the exercise.

## What's provided

Your catalog is the public **H&M Personalized Fashion Recommendations** dataset on Hugging Face: [huggingface.co/datasets/Qdrant/hm_ecommerce_products](http://huggingface.co/datasets/Qdrant/hm_ecommerce_products). It's 105K real H&M products with names, descriptions, colors, garment types, and CDN-hosted images.

**Sample 600 products** from it to build your catalog. How you sample is your call — explain the choice in your README.

**You generate the shopper profiles yourself.** Create 3–5 personas, each with whatever signal you think a real PDP system would have access to (browsing history, past purchases, demographics, declared preferences, session context — your call). The shape, fields, and richness of your profile model is itself part of what we're evaluating.

**You build the repo from scratch.** Stack, structure, dependencies — all your call.

## Must-haves

1. A web-served PDP that renders for a given `(product_id, shopper_id)` and visibly changes when either changes.
2. A **profile switcher** in the UI (dropdown of your 3–5 shoppers, plus one **"anonymous visitor"** option). Reviewers should be able to see personalization at work without writing code.
3. **At least three personalized modules** on the page. Examples — you pick which three:
   - A recommendation carousel (_"Complete the look"_, _"You might also like"_, _"Customers like you bought"_)
   - Personalized hero copy or value props (LLM-generated or rule-based)
   - Ranked reviews (top 3 reviews most relevant to this shopper)
   - Size or fit suggestion
   - Personalized urgency / scarcity / social proof
   - Anything else you'd actually ship
4. A **README** explaining your signal model, ranking strategy, and the tradeoffs you made.

## Nice-to-haves (only if you have time)

- Cold-start handling beyond "show popular items" (anonymous visitor should still feel considered)
- Explore/exploit logic so the system isn't deterministic on every reload
- Real-time signal incorporation (e.g., "add to cart" updates downstream modules)
- A simple offline metric you'd track to know if personalization is working

## Out of scope

- Auth, payments, real checkout
- Deployment or hosting
- Training your own recommendation model from scratch (use libraries or simple heuristics — we're not evaluating ML research)
- A full storefront beyond the PDP


## Deliverables

1. A **GitHub repo you create**
2. Your **README** with setup instructions, a description of your shopper profile schema, your ranking approach, and a _Tradeoffs_ section.
3. A short **Loom (~5 min)** walking us through the live PDP for at least two different shoppers, showing how the experience differs. **The Loom is the most important deliverable** — don't skip it.

## FAQ

**How realistic do my shopper profiles need to be?** Realistic enough to support interesting personalization. A profile with one field ("likes blue") is too thin; a profile with 40 fields you don't use is overdesigned. Aim for the shape a real Shopify app would actually have.

**Which LLM provider should I use?** Whichever you're comfortable with — OpenAI, Anthropic, Gemini, local. We don't have a preference. If you need credits, let us know. And it's fine to use _no_ LLM if you can't justify one.

**Do I need to deploy it?** No. Running locally is fine. Just make sure your README has a clean setup story.

**Can I use recommendation libraries (Surprise, implicit, LightFM, etc.)?** Yes — we're not testing whether you can hand-roll matrix factorization. But be ready to explain _why_ in your Loom. Reaching for a library where 20 lines of rules-based logic would do is itself a signal.

**What about embeddings / vector search?** Reasonable for some of this (e.g., "similar products" carousel). Probably overkill for others. We want to see you make that call deliberately.

**Can I just use the same product for every demo?** Technically yes, but reviewers will load a few different products to see how your system holds up. Don't hard-code to one SKU.

**Can I ask clarifying questions?** Please do — asking good questions is part of the signal. Email us anytime.
