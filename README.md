# Kinect takehome

Loom Link: https://www.loom.com/share/ab26345adb7c44878676be983e0e1e98

## Getting Started

This is a [Next.js](https://nextjs.org) application. Follow the steps below to get it running locally on your machine.

### Prerequisites

You'll need the following installed before you begin:

#### 1. Node.js

Next.js 15 requires **Node.js 18.18 or later**. We recommend using the latest LTS version.

- **Check if Node.js is installed:**
  ```bash
  node --version
  ```
- **Install Node.js** (if not already installed):
  - Download the installer from [nodejs.org](https://nodejs.org/) (LTS recommended), **or**
  - Install via [nvm](https://github.com/nvm-sh/nvm) (recommended for managing multiple Node versions):
    ```bash
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
    nvm install --lts
    nvm use --lts
    ```
  - On macOS, you can also use [Homebrew](https://brew.sh):
    ```bash
    brew install node
    ```

#### 2. npm

npm ships with Node.js, so installing Node.js will install npm automatically.

- **Check if npm is installed:**
  ```bash
  npm --version
  ```

### Installation

1. **Clone the repository:**

   ```bash
   git clone <repository-url>
   cd kinect-take-home
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```
   This will install all the packages listed in `package.json`, including Next.js, React, TypeScript, and Tailwind CSS.

### Running the Application

Start the development server:

```bash
npm run dev
```

The application will be available at [http://localhost:3000](http://localhost:3000).

## Catalog: How the 600 Products Were Sampled

- `data/products.json` — the 600 product records consumed by the app

The original data set has non-clothing products (Furniture, Stationery, Cosmetic, Interior textile, Garment and Shoe care, Fun) that are dropped from the sample. I wanted to keep the data set focused on fashion products, because that is what the personas are built around as well. There is a strong representation (56%) of products that are 'Ladieswear' and 'Baby/Children' in the original data set. I wanted to create a more balanced sample of the products, so the different personas have a similar representation of the products that they would be most interested in. An example of this is index_group 'Sport' is only 3% of the original data set, so a persona that is interested in sport would have very few products to recommend if we sampled proportionally.

| index_group   | # Rows  | Rationale                                                                          |
| ------------- | ------- | ---------------------------------------------------------------------------------- |
| Ladieswear    | 180     | Largest persona surface; needs depth across dresses, knitwear, shoes, accessories  |
| Menswear      | 150     | Override proportional bias so a male-leaning persona has real choices              |
| Divided       | 100     | H&M's younger / trend-forward line — distinct style signal from Ladieswear         |
| Baby/Children | 100     | Enables a "parent / gifting" persona                                               |
| Sport         | 70      | Massively overweighted vs. the ~3% raw share, so an "activewear" persona is viable |
| **Total**     | **600** |                                                                                    |

The embedding columns 'bge_embedding' and 'splade_embedding' are not used. Our recommendations are rule and points based so there is no need for embeddings.

There are two columns that we added to each of the sampled products.

- 'price_usd' is the current price of the product. This is used to notify users of items for sale since they added a product to their wishlist.
- 'stock_by_size' is the current stock of the product by size. This is used to notify users of items that are low in stock since they added a product to their wishlist.

Full breakdown — including per-stratum sample sizes and color coverage — is in `data/catalog_stats.json`.

### Synthetic data used for personalized modules
- data/purchase_history_personas.json is a syntheticdata set that consists of 100 more personas. They act as customers that have purchases products from the store, and have left reviews. About 30 customers have left reviews.

## Personalized Modules

### Customers like you bought

Using the synthetic customer base (purchase_history_personas.json), we use a hard filter and score function to select top 5 customer that is most similar to the current persona.
The hard filter that is applied first is

- gender_presentation
  The reason for this is a definite match for the current persona.

Following is the score function that is applied to the remaining customers:
Soft score per customer. Higher = better lookalike.
- +2 age_band exact match
- +1 per shared style_archetype
- +2 top index_group in current's top-2
- +2 price_band ranges overlap
- +1 per shared field in current's top-2 value_priorities ranks (max +2)
- +1 per shared segment
- +1 last_order_at within 30 days
- +0.5 climate exact match
- -2 return_rate > 0.3

The reason for a score function vs a hard filter on the remaining fields is that the fields hold different values for each customer, and a hard filter may remove customers that are very similar in all fields but one.
For example, a customer in the age band 35-44 can still have similar value priorities to a customer in the age band 45-54.
All the fiends seem to compare to the current persona for matching but last_order_at within 30 days and return_rate > 0.3 are not. The reason for this we want to give some weight to customers who are recent buyers so the current persona can see more current purchases. And return_rate > 0.3 is a negative signal, so that the current persona does not follow the buying behavior of a high returner.

After getting the score of the customers, we select the top 5 customers. If there are ties, we select the customer with higher total items purchased. From the 5 customers, we count every product the customers purchased using article_id. The top 8 products are recommend to the current persona.

Trade offs:

- Using a hard filter on gender_presentation, it always filters out customers that are not the same gender as the current persona but it doesn't help when user is shopping for someone else or someone else is shopping on users account (no consideration for recent searches, browsing history)
- Scoring function allows for flexibility in the weights of the fields, but how to score the pts for each field accurately can be difficult. If this is a route for improvement, we will have to come up with different scoring systems and see what system converts better.
- Yes, number of purchases made on a product is a strong signal because it is the ultimate signal for if similar customers would
  purchase the product, but it doesn't consider users current interests by using (search history, browsing history)

### Wishlist Display

Using the data of personas wishlist, we can display the wishlist items in a carousel on the PDP.
We prioritize items that are on sale or low in stock. We display this information to the user, so they see the urgency of the item if the item is low in stock. and the discount of the item since they added it to their wishlist.

Trade offs:

- Wishlist is a strong signal that a user wants that particular product. It could be that the product didn't fit the user's price band at the time they added it to their wishlist. This is why we prioritize displaying items that are on sale or low in stock. A downside to this could be now that user sees the item on sale and not low in stock, they will continue to wait to purchase the item.
- Anonymous shoppers do not have a wishlist, so we can only display the wishlist items for identified users.
- Some users may not have any items on a wishlist, so we would not have any items to display. Need a fallback display.

### Chat system that knows reviews of the current product from similar customers

We want to initiate a conversation with the user about the current product by giving a summary/highlight of the reviews of the current product written by similar customers.

What reviews are chosen and given to the llm?
We use the same hard filter and scoring function as the 'Customers like you bought'. The only difference is we also check if the similar customer has written a review for the current product.

This allows the current user to read a quick summary of the reviews that are most relevant to them. For example, someone who values comfort will leave a different review than someone who values trends the most. After the user reads the summary, they can ask the llm questions about the product or the reviews.

There could be a case where a similar customer has not written a review. In that case, we pass the top 5 highly rated reviews to the llm. The top 5 highly rated reviews are also used for anonymous shoppers.

Trade offs:

- A lot of reviews from different types of customers are needed to give a meaningful review summary based on persona
- Convenience of the user not having to scroll to the reviews section and being able to ask questions about the product or the reviews.
- Cost of tokens. By messaging the user first through the chat widget, we are using more tokens that if we were waiting for the user to ask a question or just simply displaying the reviews.
- No data on whether providing the most relevant reviews to the user will lead to a more engaging conversation. This is data that would need to be collected through tracing or session data.

Note:
- Some products do not have reviews, resulting in the chat not messaging first.
- I only have 40 or so products uploaded to the live db that the chat widget is connected to. Meaning the chat widget may not be able to answer the question correctly.
 
## Persona Fields

- **demographics** — basic demographic facts about the shopper
  - **age_band** — life-stage bucket: `18-24`, `25-34`, `35-44`, `45-54`, `55+`
  - **gender_presentation** — which catalog section the shopper primarily browses: `feminine`, `masculine`, `neutral`
  - **location**
    - **climate** — `cold`, `temperate`, `hot`; influences seasonal taste

- **declared** — preferences the shopper explicitly told us (signup form, style quiz, or account settings)
  - **sizes** — the shopper's declared sizes; optional per category
    - **top** — letter-size for tops, dresses, knitwear: `XS` / `S` / `M` / `L` / `XL`
    - **bottom** — numeric waist for trousers, skirts, shorts: `24`–`36`
    - **shoe** — numeric shoe size: `6`–`12`
  - **style_archetypes** — 1–3 style labels chosen from a quiz
    - **minimalist** — clean lines, neutral palette, fewer trend pieces
    - **streetwear** — urban/casual, statement pieces
    - **classic** — timeless cuts, wardrobe staples
    - **trend** — newest drops, fashion-forward looks
    - **athleisure** — performance-meets-casual
    - **bohemian** — flowy, eclectic, layered
  - **value_priorities** — strict ranking 1–5 (1 = most important, no ties)
    - **quality** — material substance, longevity
    - **comfort** — fit feel, fabric softness
    - **sustainability** — ethics, materials, brand values
    - **price** — budget-consciousness
    - **trend** — staying on trend, newness

- **purchase_history**
  - **orders** — list of past orders; each order is just `{ article_ids: string[] }` — the items they bought, no per-order metadata

- **browse_history**
  - **wishlist** — items the shopper saved for later; each entry snapshots the state at the moment of adding so we can detect _changes_ since then
    - **article_id** — product reference
    - **added_at** — ISO timestamp the item was wishlisted
    - **price_at_add** — display price at add-time; compared against current price to detect sales
    - **stock_at_add_in_my_size** — stock count for the shopper's declared size at add-time; compared against current stock to detect low-stock drops

- **segments** — free-form cohort tags applied by the merchant or by automation (`repeat_buyer`, `new_parent`, `gen_z`, `values_led`, etc.)

- **affinities** — inferred preferences, derived nightly from purchase + dwell-weighted browse history
  - **index_groups** — weighted preference per top-level catalog section, e.g. `{ "Ladieswear": 0.7, "Sport": 0.3 }`
  - **price_band** — typical spending range, robust to outliers (one $200 jacket doesn't blow the median)
    - **p25** — 25th percentile of prices in their activity (the cheap end of what they buy)
    - **median** — the middle of their typical spend
    - **p75** — 75th percentile (the expensive end)

### How would the persona fields be collected in a real application?

- demographics: derived from shipping address (climate via zip lookup) + signup form (age, gender). Standard Shopify Customer fields plus one computed enrichment (climate).

- declared: typical output of a Shopify-integrated style quiz (Octane AI / Shop Quiz / KnoCommerce). Stored as Klaviyo profile properties or Shopify customer metafields.

- segments: Shopify customer tags, Klaviyo segments

- affinities: pre-computed nightly from purchase_history
