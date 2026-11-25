# Interview notes: E-commerce project

Answers to the guide's "before adding the project to your resume" checklist. Re-check each
one against your own understanding, and be ready to open the file that backs it up.

**The problem in 30 seconds**
> An online marketplace wanted to know where its revenue comes from and what is hurting
> customer satisfaction. I analysed about 98k orders over 20 months. Revenue grew 138% year on year
> but has plateaued. It is concentrated in São Paulo and a handful of categories. The clearest
> problem is delivery: orders that arrive more than a week late average 1.7 stars against 4.3
> for on-time orders, and late deliveries cluster in the Northeast. So I recommended fixing
> Northeast fulfilment before spending on growth there.

**Dataset source, structure and limitations**
- Olist on Kaggle: 9 tables linked by `order_id`, `customer_id`, `product_id` and `seller_id`.
- The trap: `customer_id` is new for every order, so repeat buyers need `customer_unique_id`.
- No cost data, so no profitability. Reviews are optional. 2016 and Sep–Oct 2018 are partial, so I excluded them.

**How I cleaned the data and handled missing values**
- Kept IDs and zip codes as text so leading zeros survive.
- 610 products with no category became `unknown`, so their sales still count.
- Orders with no delivery date stay in the data but are excluded from the delay metric only.
- Dropped multi-line comment text because it broke CSV imports; kept a `has_comment` flag.
- Every change is listed in `Dataset/cleaned/cleaning_log.csv`.

**SQL joins and calculations**
- `fact_orders` view: items and reviews are aggregated to one row per order *in CTEs before
  the join*. Joining raw items to payments would multiply rows and inflate revenue.
- `fact_order_items` view: item grain, used for category revenue.
- Used CASE WHEN for the late flag and delivery buckets, LAG() for month-over-month growth,
  RANK() for category ranks, and SUM() OVER () for shares of total.

**KPIs and formulas**
- Revenue = SUM(price) of valid orders (not canceled/unavailable), freight excluded.
- AOV = revenue / COUNT(DISTINCT order_id) = R$137.37.
- Late % = late delivered orders / delivered orders with a date = 6.79%.

**How I validated**
- SQL total = pandas total (R$13,449,529.68).
- Monthly, category and state sums each equal the total.
- Items + freight vs payments: 0.018% difference.
- Dashboard numbers match SQL, including under filters.

**Three real findings**
1. +138% YoY growth driven by volume (AOV flat), now flat at about R$0.9M per month.
2. Late delivery is strongly associated with poor reviews (1–2 star share 9% → 79%).
3. 97% of customers buy once.

**Justify a recommendation**
> Prioritise Northeast fulfilment. The Northeast's late rate is 12.8%, double the Southeast's,
> and late orders are where 1–2 star reviews concentrate. Northeast customers also spend about 26% more per order,
> so the customers we are disappointing are valuable ones. This is correlation, so I'd propose an
> A/B test of a carrier change before claiming it raises reviews.

**Additional data I'd ask the business for**
Product cost and commission (margin), marketing spend by channel (CAC/ROAS), carrier IDs
(which partner causes delays), and data after Aug 2018 (does the plateau continue?).
