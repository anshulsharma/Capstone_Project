import json
import os
import sys
from datetime import datetime
from pathlib import Path

from google import genai
from google.genai import types

ROOT = Path(__file__).resolve().parent.parent
FINDINGS_PATH = ROOT / "narrator" / "findings.json"
SAMPLE_PATH = ROOT / "narrator" / "sample_output.txt"
MODEL = "gemini-2.5-flash"  # if this name errors, copy a current model name from AI Studio

SYSTEM_INSTRUCTION = """You are a senior data analyst writing for Mamaearth's regional ops and finance heads.

Write a business narrative of about 250 words with exactly three labeled sections, in this order:
Situation
Complication
Resolution

Use only the numbers supplied in the user's message. Copy each number exactly as given, with the same value and units. Do not invent, estimate, or round any statistic, and do not add figures that are not in the input.
Write in plain business English. Do not use markdown headings other than the three section labels."""



def build_prompt(findings):
    pm = findings["return_rate_by_payment"]
    seg = findings["highest_risk_segment"]
    peak = findings["true_peak_month"]
    infl = findings["outlier_inflated_month"]
    return f"""Findings from the Mamaearth returns analysis:
- Cleaned total order revenue: INR {findings['cleaned_total_revenue_inr']:,.2f}
- Raw total order revenue before cleaning: INR {findings['raw_total_revenue_inr']:,.2f}
- Duplicate-driven reconciliation delta: INR {findings['duplicate_reconciliation_delta_inr']:,.2f}
- Return rate by payment method: COD {pm['COD']}%, CARD {pm['CARD']}%, UPI {pm['UPI']}%
- Highest-risk segment: {seg['payment_method']} orders in Tier {seg['city_tier']} cities, return rate {seg['return_rate_pct']}%
- True peak month (outliers excluded): {peak['month']}, INR {peak['revenue_inr']:,.2f}
- Outlier-inflated month: {infl['month']}, apparent INR {infl['apparent_revenue_inr']:,.2f}, corrected INR {infl['corrected_revenue_inr']:,.2f}

Write the Situation, Complication and Resolution for the regional ops and finance heads."""




def generate_scr_narrative(findings):
    try:
        client = genai.Client()  # reads GEMINI_API_KEY from the environment
        response = client.models.generate_content(
            model=MODEL,
            contents=build_prompt(findings),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                # Deterministic output: this is a factual business report, not creative writing.
                temperature=0.0,
                # Explicit limit, well above the ~250 words the narrative needs.
                max_output_tokens=600,
                # Timeout is in milliseconds. 30000 = 30 seconds, above the 10-second minimum.
                http_options=types.HttpOptions(timeout=30000),
            ),
        )
        text = response.text
        if not text:
            raise ValueError("Empty response from Gemini")
        tokens = response.usage_metadata.total_token_count if response.usage_metadata else None
        return {"status": "success", "narrative": text, "tokens": tokens}
    except Exception as err:
        # The caller never receives a raw exception.
        return {"status": "error", "narrative": None, "message": str(err)}



def generate_scr_narrative_offline(findings):
    pm = findings["return_rate_by_payment"]
    seg = findings["highest_risk_segment"]
    peak = findings["true_peak_month"]
    infl = findings["outlier_inflated_month"]
    peak_name = datetime.strptime(peak["month"], "%Y-%m").strftime("%B")  # "March"
    infl_name = datetime.strptime(infl["month"], "%Y-%m").strftime("%B")  # "January"

    text = f"""Situation
Mamaearth's cleaned order book totals INR {findings['cleaned_total_revenue_inr']:,.2f} across 175 valid orders. The raw extract reported INR {findings['raw_total_revenue_inr']:,.2f}, so the first step was to reconcile the two figures before trusting any trend.

Complication
The gap of INR {findings['duplicate_reconciliation_delta_inr']:,.2f} comes entirely from five duplicate orders caused by double submissions. Imputing missing discounts and ratings does not change any order value. Returns are also concentrated in COD orders, which return at {pm['COD']}% compared with {pm['CARD']}% for Card and {pm['UPI']}% for UPI. The highest-risk segment is COD orders in Tier {seg['city_tier']} cities, at a {seg['return_rate_pct']}% return rate. Revenue also looks misleadingly strong in {infl_name}: the apparent figure of INR {infl['apparent_revenue_inr']:,.2f} is driven by two bulk orders, and the corrected figure is INR {infl['corrected_revenue_inr']:,.2f}.

Resolution
Focus return-reduction efforts on COD orders in Tier {seg['city_tier']} cities, since that is where the loss is concentrated. Plan inventory and staffing around {peak_name}, the true peak month, with revenue of INR {peak['revenue_inr']:,.2f} once the outliers are excluded."""

    return {"status": "success", "narrative": text, "tokens": None}



REQUIRED_FIGURES = [
    ("97358.30", "cleaned total revenue"),
    ("44.4", "COD return rate"),
    ("54.5", "COD + Tier-2 highest-risk segment return rate"),
    ("2501.90", "duplicate reconciliation delta"),
    ("March", "true peak month name"),
    ("20318.90", "true peak month revenue"),
]

def check_narrative(text):
    normalized = text.replace(",", "")
    all_ok = True
    for needle, label in REQUIRED_FIGURES:
        ok = needle in normalized
        all_ok = all_ok and ok
        print(f"[{'PASS' if ok else 'FAIL'}] {label}: {needle}")
    return all_ok



def build_narrative(findings):
    if os.environ.get("GEMINI_API_KEY"):
        result = generate_scr_narrative(findings)
        if result["status"] == "success":
            return result, "online"
        print("Online call failed, using offline fallback:", result["message"])
    else:
        print("No GEMINI_API_KEY set, using offline fallback.")
    return generate_scr_narrative_offline(findings), "offline"

if __name__ == "__main__":
    if "--check-sample" in sys.argv:
        ok = check_narrative(SAMPLE_PATH.read_text(encoding="utf-8"))
        print("ALL PASS" if ok else "SOME CHECKS FAILED")
        sys.exit(0 if ok else 1)

    with open(FINDINGS_PATH, encoding="utf-8") as f:
        findings = json.load(f)

    result, path = build_narrative(findings)
    print(f"Path used: {path}\n")
    print(result["narrative"])

    if path == "online":
        SAMPLE_PATH.write_text(result["narrative"], encoding="utf-8")
        print(f"\nSaved online output to {SAMPLE_PATH}")

    print("\nChecker results:")
    ok = check_narrative(result["narrative"])
    print("ALL PASS" if ok else "SOME CHECKS FAILED")