import json
from pathlib import Path
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
with open(ROOT / "narrator" / "findings.json") as f:
    findings = json.load(f)

VIS = ROOT / "visualizations"
VIS.mkdir(exist_ok=True)

# Chart 1: return rate by payment method, descending, labeled bars
rates = dict(sorted(findings["return_rate_by_payment"].items(),
                    key=lambda kv: kv[1], reverse=True))
cod, card = findings["return_rate_by_payment"]["COD"], findings["return_rate_by_payment"]["CARD"]

fig, ax = plt.subplots(figsize=(7, 4.5))
bars = ax.bar(list(rates.keys()), list(rates.values()), color="#c0392b")
for bar, val in zip(bars, rates.values()):
    ax.text(bar.get_x() + bar.get_width() / 2, val + 0.5, f"{val}%", ha="center")
ax.set_ylabel("Return rate (%)")
ax.set_xlabel("Payment method")
ax.set_title(f"COD Returns at {cod}% — {cod / card:.1f}x Card")
fig.tight_layout()
fig.savefig(VIS / "return_rate_by_payment.png", dpi=150)

# Chart 2: outlier-corrected monthly revenue trend
monthly = findings["monthly_revenue_corrected_inr"]
peak = findings["true_peak_month"]["month"]

fig, ax = plt.subplots(figsize=(8, 4.5))
ax.plot(list(monthly.keys()), list(monthly.values()), marker="o", color="#2c3e50")
ax.set_xlabel("Month")
ax.set_ylabel("Revenue (INR)")
ax.set_title(f"Monthly Revenue (Outliers Excluded): Peak in {peak}")
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(VIS / "monthly_revenue_trend.png", dpi=150)

print("Saved visualizations to", VIS)