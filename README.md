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

- A scoring function gives us flexibility to adjust the weight of each field, but assigning accurate point values to those fields is challenging. If we pursue this approach, we will need to design and test multiple scoring systems to determine which one leads to better conversion.
- The number of times a product is purchased is a strong signal of whether similar customers are interested in it, since purchases are the clearest indicator of interest. However, this signal does not capture a user’s current intent because it ignores PDP data such as search history and browsing history. 

### Wishlist Display

We can use persona wishlist data to show wishlist items in a carousel on the PDP. Items that are on sale or low in stock should be prioritized. Displaying low-stock status can create urgency, while showing the discount since the item was added to the wishlist can reinforce the value of purchasing now.

Trade offs:

- Wishlist is a strong signal that a user wants that particular product. It could be that the product didn't fit the user's price band at the time they added it to their wishlist. This is why we prioritize displaying items that are on sale or low in stock. A downside to this could be that now that the user sees the item on sale and not low in stock, they will continue to wait to purchase the item.
- Anonymous shoppers do not have a wishlist, so we can only display the wishlist items for identified users. And identified users may not have any items on a wishlist, so we would not have any items to display. Meaning we need a fallback display.

### Chat system for reviews from similar customers
We want to start a conversation with the user about the current product by showing a summary of reviews written by similar customers.

Which reviews are sent to the LLM?
We use the same hard filter and scoring function as the “Customers like you bought” system. The only additional requirement is that the similar customer must have written a review for the current product.

Why this helps
This approach gives the user a quick summary of the reviews that are most relevant to them. Different customers care about different product qualities. For example, a customer who prioritizes comfort may write a very different review from someone who cares most about style or trends. After reading the summary, the user can ask the LLM follow-up questions about the product or the reviews.

Fallback case
In some cases, no similar customer will have written a review for the current product. When that happens, we send the top five highest-rated reviews to the LLM instead. We also use these top five reviews for anonymous shoppers.

Trade offs:

- A meaningful persona-based review summary requires a large and diverse set of reviews from different customer types.
- This improves convenience for the user by removing the need to scroll to the reviews section and allowing them to ask follow-up questions about the product or the reviews directly.
- There is a token cost tradeoff. If we proactively send the first message through the chat widget, we use more tokens than if we wait for the user to start the conversation or simply show the reviews without chat. Meaning, we need to collect data showing whether summarizing and showing the most relevant reviews leads to more engaging conversations. To answer this, we would need to collect and analyze tracing or session-level data.

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
