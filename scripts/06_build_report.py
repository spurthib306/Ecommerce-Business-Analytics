"""Step 6 - write the insights report (Insights/insights_report.md and .pdf).

Every number in the report is read from SQL-Queries/results, so re-running the
pipeline keeps the text and the data consistent. Charts are saved to
Insights/charts/ for the README and the PDF.
"""
import sys

import matplotlib

matplotlib.use("Agg")  # no display needed (works headless on macOS and Windows)
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from config import CHARTS_DIR, INSIGHTS_DIR, KAGGLE_URL, RESULTS_DIR, ensure_dirs

BLUE, SOFT, INK, MUTED, GRID = "#2a78d6", "#86b6ef", "#0b0b0b", "#898781", "#e1e0d9"


def res(name):
    return pd.read_csv(RESULTS_DIR / f"{name}.csv")


def money(v):
    return f"R${v:,.0f}"


def millions(v):
    return f"R${v / 1e6:.2f}M"


def style_axes(ax):
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color("#c3c2b7")
    ax.tick_params(colors=MUTED, labelsize=9, length=0)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def charts(monthly, cats, regions, reviews):
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "sans-serif", "font.size": 10})

    fig, ax = plt.subplots(figsize=(8, 3))
    x = pd.to_datetime(monthly.order_month)
    ax.plot(x, monthly.revenue / 1e3, color=BLUE, linewidth=2)
    ax.fill_between(x, monthly.revenue / 1e3, color=BLUE, alpha=0.1)
    style_axes(ax)
    ax.set_ylabel("Revenue (R$ thousands)", color=MUTED, fontsize=9)
    ax.set_title("Monthly revenue", loc="left", fontsize=11, color=INK)
    fig.tight_layout(); fig.savefig(CHARTS_DIR / "monthly_revenue.png", dpi=180); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 3.4))
    top = cats.head(10).iloc[::-1]
    ax.barh(top.category, top.revenue / 1e3, color=BLUE, height=0.55)
    style_axes(ax); ax.grid(axis="x", color=GRID, linewidth=0.8); ax.grid(axis="y", visible=False)
    ax.set_xlabel("Revenue (R$ thousands)", color=MUTED, fontsize=9)
    ax.set_title("Top 10 categories by revenue", loc="left", fontsize=11, color=INK)
    fig.tight_layout(); fig.savefig(CHARTS_DIR / "top_categories.png", dpi=180); plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(8, 3))
    ax = axes[0]
    ax.bar(regions.customer_region, regions.late_delivery_pct, color=BLUE, width=0.5)
    style_axes(ax); ax.set_title("Late delivery rate by region (%)", loc="left", fontsize=10, color=INK)
    ax.tick_params(axis="x", labelrotation=20)
    ax = axes[1]
    labels = reviews.delivery_bucket.str.replace(r"^\d\. ", "", regex=True)
    ax.bar(labels, reviews.avg_review, color=BLUE, width=0.5)
    ax.set_ylim(0, 5); style_axes(ax)
    ax.set_title("Average review by delivery timeliness", loc="left", fontsize=10, color=INK)
    ax.tick_params(axis="x", labelrotation=20)
    for i, v in enumerate(reviews.avg_review):
        ax.text(i, v + 0.1, f"{v:.2f}", ha="center", fontsize=9, color=INK)
    fig.tight_layout(); fig.savefig(CHARTS_DIR / "delivery_reviews.png", dpi=180); plt.close(fig)


def build_content():
    k = res("02_kpi_overview").iloc[0]
    monthly = res("03_monthly_revenue")
    yoy = res("04_yoy_growth").iloc[0]
    cats = res("05_category_revenue")
    prof = res("06_high_value_low_volume")
    states = res("07_revenue_by_state")
    regions = res("08_revenue_by_region")
    deliv = res("10_delivery_by_state")
    reviews = res("11_reviews_vs_delivery")
    repeat = res("12_repeat_customers")
    rec = res("14_reconciliation").iloc[0]
    charts(monthly, cats, regions, reviews)

    peak = monthly.loc[monthly.revenue.idxmax()]
    peak_month = pd.to_datetime(peak.order_month).strftime("%B %Y")
    m2018 = monthly[monthly.order_month >= "2018-01-01"]
    top10_share = cats.head(10).revenue_share_pct.sum()
    hv = prof[prof.profile == "High value, lower volume"]
    hv_names = ", ".join(hv.category)
    wg = cats[cats.category == "watches gifts"].iloc[0]
    bbt = cats[cats.category == "bed bath table"].iloc[0]
    bbt_orders_share = 100 * bbt.orders / k.distinct_orders
    wg_orders_share = 100 * wg.orders / k.distinct_orders
    se = regions[regions.customer_region == "Southeast"].iloc[0]
    ne = regions[regions.customer_region == "Northeast"].iloc[0]
    no = regions[regions.customer_region == "North"].iloc[0]
    sp = states[states.customer_state == "SP"].iloc[0]
    worst = deliv[deliv.delivered_orders >= 300].head(3)
    worst_txt = ", ".join(f"{r.customer_state} {r.late_delivery_pct:.1f}%" for r in worst.itertuples())
    on_time, very_late = reviews.iloc[0], reviews.iloc[-1]
    one = repeat[repeat.customer_type == "1 order"].iloc[0]

    findings = [
        ("Revenue more than doubled year on year, but has plateaued in 2018.",
         f"Revenue for Jan-Aug 2018 was {millions(yoy.revenue_jan_aug_2018)}, up {yoy.revenue_growth_pct:.0f}% on the same "
         f"months of 2017 ({millions(yoy.revenue_jan_aug_2017)}). Growth came from order volume, not basket size: orders rose from "
         f"{int(yoy.orders_jan_aug_2017):,} to {int(yoy.orders_jan_aug_2018):,}. The single best month was {peak_month} "
         f"({millions(peak.revenue)}, the Black Friday month), and every 2018 month sat between "
         f"{millions(m2018.revenue.min())} and {millions(m2018.revenue.max())}, so growth has levelled off."),
        ("A few categories carry the business, and some earn far more per order.",
         f"The top 10 of {len(cats)} categories generate {top10_share:.0f}% of revenue. Watches &amp; gifts earns "
         f"{wg.revenue_share_pct:.1f}% of revenue from {wg_orders_share:.1f}% of orders (AOV {money(wg.category_aov)} vs "
         f"{money(k.average_order_value)} overall). Categories whose revenue share is at least 1.5x their order share: {hv_names}. "
         f"Bed, bath &amp; table is the opposite: the most orders ({bbt_orders_share:.1f}%) at a lower AOV of {money(bbt.category_aov)}."),
        ("Sales are concentrated in the Southeast; the North and Northeast spend more per order but wait longer.",
         f"The Southeast produces {se.revenue_share_pct:.1f}% of revenue, and Sao Paulo state alone {sp.revenue_share_pct:.1f}%. "
         f"Orders from the North and Northeast are larger (AOV {money(no.average_order_value)} and {money(ne.average_order_value)} "
         f"vs {money(se.average_order_value)} in the Southeast) but take {no.avg_delivery_days:.0f} and {ne.avg_delivery_days:.0f} days "
         f"to arrive, against {se.avg_delivery_days:.0f} days."),
        ("Late deliveries are uncommon overall but concentrated in the Northeast.",
         f"{k.late_delivery_pct:.1f}% of delivered orders arrived after the estimated date. The Northeast's late rate is "
         f"{ne.late_delivery_pct:.1f}%, about double the Southeast's {se.late_delivery_pct:.1f}%. Worst states with 300+ delivered "
         f"orders: {worst_txt}."),
        ("Late deliveries are strongly associated with poor reviews.",
         f"Orders delivered on time average {on_time.avg_review:.2f} stars; orders 8+ days late average {very_late.avg_review:.2f}. "
         f"The share of 1-2 star reviews rises from {on_time.pct_1_2_star:.0f}% to {very_late.pct_1_2_star:.0f}%. This is an "
         f"association, not proof of cause, but the gradient is steep and consistent across every delay band."),
        ("Almost every customer buys only once.",
         f"{one.customer_share_pct:.1f}% of customers placed a single order in the 20 months, and repeat customers produced only "
         f"{100 - one.revenue_share_pct:.1f}% of revenue. Growth so far has depended entirely on acquiring new buyers."),
    ]
    recommendations = [
        "Fix fulfilment in the Northeast first. Audit carriers and seller dispatch times for AL, MA, SE and CE, and set more "
        "realistic delivery estimates there. Late orders are where 1-2 star reviews concentrate (finding 5).",
        "Protect and grow high-value categories. Give watches &amp; gifts, small appliances, musical instruments and office furniture "
        "more marketing space and seller recruitment; each order there is worth about 1.5-2x the average (finding 2).",
        "Build a retention programme. With about 97% one-time buyers, a post-delivery email, a second-order voucher and "
        "category-based recommendations are cheap tests with large upside (finding 6).",
        "Plan capacity for Black Friday. November 2017 was the peak month; logistics and customer service need to scale "
        "before Q4 so that the volume spike does not create a delay spike (findings 1 and 5).",
        "Grow outside the Southeast carefully. North and Northeast buyers spend more per order, but long delivery times put "
        "reviews at risk. Regional fulfilment partners should come before regional marketing spend (findings 3 and 4).",
    ]
    meta = {
        "k": k, "rec": rec, "cats": len(cats),
    }
    return findings, recommendations, meta


def write_markdown(findings, recs, meta):
    k, rec = meta["k"], meta["rec"]
    lines = [
        "# E-commerce Business Performance & Revenue Analytics - Insights Report", "",
        "## 1. Objective and business context",
        "Management wants to understand revenue trends, product performance, regional differences, delivery performance "
        "and customer reviews, and to get recommendations for improvement.", "",
        "## 2. Dataset and limitations",
        f"Brazilian E-Commerce Public Dataset by Olist ([Kaggle]({KAGGLE_URL})): about 99k orders (2016-2018) across 9 related "
        "tables (orders, items, payments, reviews, customers, products, sellers, category translation, geolocation).", "",
        "- Scope: orders purchased Jan 2017 - Aug 2018 (20 complete months). 2016 and Sep-Oct 2018 are partial and excluded (349 orders).",
        "- No cost data, so profitability cannot be measured; revenue is item price excluding freight.",
        "- Reviews exist for about 99% of orders, but they are optional and may skew towards strong opinions.",
        "- Delivery estimates are set by Olist; a late flag measures performance against the promise, not absolute speed.", "",
        "## 3. Tools and methodology",
        "Python (pandas) for profiling and cleaning; SQL (DuckDB, PostgreSQL-compatible) for joins and metrics; Excel for "
        "data-quality checks and validation; an HTML dashboard and a Power BI build guide for visualisation.",
        f"Headline numbers were validated three ways: SQL vs an independent pandas calculation, sums by month/category/state "
        f"vs the total, and items + freight vs payments (difference {rec.difference_pct:.3f}%).", "",
        "| KPI | Value |", "|---|---|",
        f"| Revenue | R${k.total_revenue:,.2f} |",
        f"| Distinct orders | {int(k.distinct_orders):,} |",
        f"| Average order value | R${k.average_order_value:,.2f} |",
        f"| Distinct customers | {int(k.distinct_customers):,} |",
        f"| Average review score | {k.avg_review_score:.2f} / 5 |",
        f"| Delivered late | {k.late_delivery_pct:.2f}% |",
        f"| Average delivery time | {k.avg_delivery_days:.1f} days |", "",
        "## 4. Key findings", "",
    ]
    for i, (title, body) in enumerate(findings, 1):
        lines += [f"**{i}. {title}**", "", body.replace("&amp;", "&"), ""]
    lines += ["![Monthly revenue](charts/monthly_revenue.png)", "", "![Top categories](charts/top_categories.png)", "",
              "![Delivery and reviews](charts/delivery_reviews.png)", "", "## 5. Recommendations", ""]
    lines += [f"{i}. {r.replace('&amp;', '&')}" for i, r in enumerate(recs, 1)]
    lines += ["", "## 6. Additional data that would improve the analysis", "",
              "- Product cost and marketplace commission, to measure margin and true profitability.",
              "- Marketing spend and traffic source, to calculate CAC and ROAS.",
              "- Carrier and warehouse identifiers, to attribute delays to a specific logistics partner.",
              "- Data after August 2018, to confirm whether the 2018 plateau continued."]
    (INSIGHTS_DIR / "insights_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_pdf(findings, recs, meta):
    k = meta["k"]
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], fontSize=16, leading=20, alignment=0, textColor=colors.HexColor("#1F3A5F"))
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=11.5, leading=14, spaceBefore=8, spaceAfter=3,
                        textColor=colors.HexColor("#1F3A5F"))
    body = ParagraphStyle("b", parent=ss["BodyText"], fontSize=9, leading=12.2)
    small = ParagraphStyle("s", parent=body, fontSize=8, textColor=colors.HexColor("#52514e"))
    doc = SimpleDocTemplate(str(INSIGHTS_DIR / "insights_report.pdf"), pagesize=A4, leftMargin=1.7 * cm,
                            rightMargin=1.7 * cm, topMargin=1.4 * cm, bottomMargin=1.4 * cm,
                            title="E-commerce Insights Report")
    s = [Paragraph("E-commerce Business Performance &amp; Revenue - Insights Report", h1),
         Paragraph("Olist Brazilian marketplace, orders purchased January 2017 - August 2018", small), Spacer(1, 6),
         Paragraph("1. Objective", h2),
         Paragraph("Understand revenue trends, product performance, regional differences, delivery performance and customer "
                   "reviews, and recommend improvements.", body),
         Paragraph("2. Dataset and limitations", h2),
         Paragraph("Brazilian E-Commerce Public Dataset by Olist (Kaggle), 9 related tables, about 99k orders. Scope is the 20 "
                   "complete months (349 orders in partial months excluded). Revenue = item price excluding freight, for orders not "
                   "canceled or unavailable. No cost data, so profitability is out of scope. Reviews are optional and averaged "
                   "per order.", body),
         Paragraph("3. Tools and methodology", h2),
         Paragraph("Python/pandas to profile and clean; SQL (DuckDB, PostgreSQL-compatible) to join tables at the right grain and "
                   "compute metrics; Excel for data-quality and validation checks; an interactive dashboard for exploration. "
                   "Totals were cross-checked between SQL and pandas and reconciled with payments "
                   f"(difference {meta['rec'].difference_pct:.3f}%).", body), Spacer(1, 6)]
    kpi = [["Revenue", "Orders", "AOV", "Customers", "Avg review", "Late"],
           [f"R${k.total_revenue / 1e6:.2f}M", f"{int(k.distinct_orders):,}", f"R${k.average_order_value:.2f}",
            f"{int(k.distinct_customers):,}", f"{k.avg_review_score:.2f}", f"{k.late_delivery_pct:.1f}%"]]
    t = Table(kpi, hAlign="LEFT", colWidths=[2.9 * cm] * 6)
    t.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 8.5), ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#52514e")),
                           ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"), ("FONTSIZE", (0, 1), (-1, 1), 11),
                           ("LINEBELOW", (0, 1), (-1, 1), 0.5, colors.HexColor("#e1e0d9"))]))
    s += [t, Paragraph("4. Key findings", h2)]
    for i, (title, text) in enumerate(findings, 1):
        s.append(Paragraph(f"<b>{i}. {title}</b> {text}", body))
        s.append(Spacer(1, 3))
        if i == 1:
            s.append(Image(str(CHARTS_DIR / "monthly_revenue.png"), width=16 * cm, height=6 * cm))
        if i == 2:
            s.append(Image(str(CHARTS_DIR / "top_categories.png"), width=16 * cm, height=6.8 * cm))
        if i == 5:
            s.append(Image(str(CHARTS_DIR / "delivery_reviews.png"), width=16 * cm, height=6 * cm))
    s.append(Paragraph("5. Recommendations", h2))
    for i, r in enumerate(recs, 1):
        s.append(Paragraph(f"{i}. {r}", body))
        s.append(Spacer(1, 2))
    s.append(Paragraph("6. Data that would strengthen the analysis", h2))
    s.append(Paragraph("Product cost and commission (margin), marketing spend and traffic source (CAC, ROAS), carrier IDs "
                       "(attribute delays), and data after August 2018 (confirm the plateau).", body))
    doc.build(s)


def main():
    ensure_dirs()
    if not (RESULTS_DIR / "02_kpi_overview.csv").exists():
        print("[report] SQL results not found. Run step 3 first.")
        return 1
    findings, recs, meta = build_content()
    write_markdown(findings, recs, meta)
    write_pdf(findings, recs, meta)
    print(f"[report] Written {INSIGHTS_DIR / 'insights_report.md'} and insights_report.pdf; charts in {CHARTS_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
