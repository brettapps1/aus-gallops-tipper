#!/usr/bin/env python3
"""Master Business Advisory Orchestrator for Fair Dinkum Publishing.

Runs the full business advisory pipeline in sequence:
  1. Market Research → discovers profitable niches
  2. Opportunity Scoring → scores and ranks opportunities
  3. Pricing → recommends optimal price point
  4. Business Adviser → strategic recommendations

Each stage feeds its output to the next. The final report is printed
to stdout (pretty JSON) and saved to a JSON file.

Usage:
  python workflow_manager/run_business_advisory.py "AI side-hustle guide for tradies"
  python workflow_manager/run_business_advisory.py "bookkeeping for freelancers" --out reports/bookkeeping.json
  python workflow_manager/run_business_advisory.py "NDIS provider startup" --max-top 3
  python workflow_manager/run_business_advisory.py "e-commerce fulfilment" --pricing-min 19.99 --pricing-max 99.99

Arguments:
  query         Product / niche / topic to analyse (positional, required)
  --out         Output JSON path (default: reports/business_advisory_<product_id>.json)
  --max-top     Max opportunities to score and pass to pricing (default: 5)
  --pricing-min Minimum price for pricing agent (default: 9.99)
  --pricing-max Maximum price for pricing agent (default: 49.99)
  --dry-run     Skip saving to RAGS memory (useful for quick iterations)
  --verbose     Print intermediate stage results to stderr
  --pretty      Pretty-print JSON output (default: true)
  --compact     Compact JSON output

Output:
  Structured JSON report with keys:
    - product_id: unique identifier for this run
    - query: original query
    - generated_at: ISO timestamp
    - market_research: full research output
    - opportunity_scoring: scored and ranked opportunities
    - pricing: pricing analysis with recommended price
    - business_advisory: strategic recommendations and next actions
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — allow running from repo root or workflow_manager/
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# ---------------------------------------------------------------------------
# Imports from the Fair Dinkum agent fleet
# ---------------------------------------------------------------------------
from app.agents.market_research import MarketResearchAgent
from app.agents.opportunity_scoring import OpportunityScoringAgent
from app.agents.pricing import PricingAgent
from app.agents.business_adviser import BusinessAdviserAgent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def generate_product_id(query: str) -> str:
    """Generate a short unique product id from query + timestamp."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    slug = "".join(c for c in query.lower() if c.isalnum())[:8]
    short_uuid = uuid.uuid4().hex[:6]
    return f"FDP-{ts}-{slug}-{short_uuid}"


def build_report(
    product_id: str,
    query: str,
    market_report: dict,
    scoring_report: dict,
    pricing_report: dict,
    advisory_report: dict,
) -> dict:
    """Compose the final advisory report."""
    return {
        "schema_version": "1.0",
        "product_id": product_id,
        "query": query,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "brand": "Fair Dinkum Publishing",
        "pipeline": "market_research → opportunity_scoring → pricing → business_advisory",
        "market_research": market_report,
        "opportunity_scoring": scoring_report,
        "pricing": pricing_report,
        "business_advisory": advisory_report,
    }


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
def run_pipeline(
    query: str,
    product_id: str,
    max_top: int = 5,
    pricing_min: float = 9.99,
    pricing_max: float = 49.99,
    verbose: bool = False,
) -> dict:
    """Execute the full business advisory pipeline."""

    # ── Stage 1: Market Research ──────────────────────────────────────────
    print(f"[1/4] Market Research — '{query}'")
    researcher = MarketResearchAgent(project_id=product_id)
    market_report = researcher.execute(query=query)

    opportunities = market_report.get("top_opportunities", [])
    if not opportunities:
        print("  ⚠ No opportunities found. Aborting pipeline.")
        return build_report(product_id, query, market_report, {}, {}, {})

    print(f"  ✓ Found {market_report.get('opportunities_found', 0)} opportunities")
    if verbose:
        for i, opp in enumerate(opportunities[:max_top], 1):
            print(f"      {i}. {opp.get('niche', 'N/A')} (score={opp.get('opportunity_score', '?')})")

    # ── Stage 2: Opportunity Scoring ──────────────────────────────────────
    print(f"[2/4] Opportunity Scoring (top {max_top})")
    scorer = OpportunityScoringAgent(project_id=product_id)

    # Transform opportunities into the format the scorer expects
    scoring_input = []
    for opp in opportunities[:max_top]:
        scoring_input.append({
            "niche": opp.get("niche", ""),
            "keyword": " ".join(opp.get("keywords", [])),
            "search_volume": opp.get("estimated_demand", "medium"),
            "competition": opp.get("competition_level", "medium"),
            "trend": opp.get("trend", "stable"),
            "audience_size": opp.get("audience_size", "medium"),
            "format": opp.get("format_suggestion", "ebook"),
        })

    scoring_report = scorer.execute(opportunities=scoring_input)
    print(f"  ✓ Scored {len(scoring_report.get('scores', []))} opportunities")

    best = scoring_report.get("best_opportunity")
    if best:
        print(f"  ★ Best: {best.get('niche', 'N/A')} (score={best.get('total_score', '?')})")

    # ── Stage 3: Pricing ──────────────────────────────────────────────────
    print(f"[3/4] Pricing Analysis")
    # Build product data from best-scored opportunity for pricing context
    product_data = None
    if best:
        matched_opp = next(
            (o for o in opportunities if o.get("niche") == best.get("niche")),
            opportunities[0] if opportunities else None,
        )
        if matched_opp:
            product_data = {
                "niche": matched_opp.get("niche", query),
                "format": matched_opp.get("format_suggestion", "ebook"),
                "estimated_demand": matched_opp.get("estimated_demand", "medium"),
                "competition_level": matched_opp.get("competition_level", "medium"),
            }

    pricing_agent = PricingAgent(
        project_id=product_id,
        pricing_config={
            "min_price": pricing_min,
            "max_price": pricing_max,
            "test_points": 5,
        },
    )
    pricing_report = pricing_agent.execute(product_data=product_data)

    rec_price = pricing_report.get("recommended_price")
    confidence = pricing_report.get("confidence")
    print(f"  ✓ Recommended price: ${rec_price} AUD (confidence: {confidence})")

    # ── Stage 4: Business Adviser ─────────────────────────────────────────
    print(f"[4/4] Business Advisory")

    # Build a lightweight product list from what we know
    products = []
    if best:
        products.append({
            "id": product_id,
            "name": best.get("niche", query),
            "price": rec_price or pricing_min,
            "sales": 0,
            "revenue": 0,
        })

    adviser = BusinessAdviserAgent(project_id=product_id)
    advisory_report = adviser.execute(query=query, products=products)

    # Handle partial failures — adviser may return report=None on internal error
    report_section = advisory_report.get("report") or {}
    recs = report_section.get("recommendations", [])
    print(f"  ✓ Advisory complete — {len(recs)} recommendations generated")

    # ── Compose final report ──────────────────────────────────────────────
    report = build_report(
        product_id=product_id,
        query=query,
        market_report=market_report,
        scoring_report=scoring_report,
        pricing_report=pricing_report,
        advisory_report=advisory_report,
    )

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fair Dinkum Publishing — Business Advisory Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "query",
        help="Product / niche / topic to analyse (e.g., 'AI side-hustle guide for tradies')",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output JSON path (default: reports/business_advisory_<product_id>.json)",
    )
    parser.add_argument(
        "--max-top",
        type=int,
        default=5,
        help="Max opportunities to score and pass to pricing (default: 5)",
    )
    parser.add_argument(
        "--pricing-min",
        type=float,
        default=9.99,
        help="Minimum price for pricing agent (default: 9.99)",
    )
    parser.add_argument(
        "--pricing-max",
        type=float,
        default=49.99,
        help="Maximum price for pricing agent (default: 49.99)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip saving to RAGS memory (RAGS writes still attempted by agents but errors are caught)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print intermediate stage results to stderr",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--pretty",
        dest="pretty",
        action="store_true",
        default=True,
        help="Pretty-print JSON output (default)",
    )
    group.add_argument(
        "--compact",
        dest="pretty",
        action="store_false",
        help="Compact JSON output",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Logging setup
    log_level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    # Generate a product id for this run
    product_id = generate_product_id(args.query)
    print(f"Product ID: {product_id}")
    print(f"Pipeline:   Market Research → Opportunity Scoring → Pricing → Business Adviser")
    print()

    # Run the pipeline
    report = run_pipeline(
        query=args.query,
        product_id=product_id,
        max_top=args.max_top,
        pricing_min=args.pricing_min,
        pricing_max=args.pricing_max,
        verbose=args.verbose,
    )

    # Determine output path
    if args.out:
        out_path = Path(args.out)
    else:
        out_dir = REPO_ROOT / "reports"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"business_advisory_{product_id}.json"

    # Write JSON report
    indent = 2 if args.pretty else None
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=indent, default=str)

    print()
    print(f"Report saved: {out_path}")

    # Print report to stdout
    print()
    print(json.dumps(report, indent=indent, default=str))


if __name__ == "__main__":
    main()
