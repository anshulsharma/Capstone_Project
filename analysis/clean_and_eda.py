import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
FINDINGS_PATH = ROOT / "narrator" / "findings.json"

# ---------- Task 1: Load and inspect ----------
orders = pd.read_csv(DATA / "orders.csv")
customers = pd.read_csv(DATA / "customers.csv")
products = pd.read_csv(DATA / "products.csv")

print("orders.shape (before cleaning):", orders.shape)
assert orders.shape == (180, 9), "orders.csv is not the expected 180 x 9"



# ---------- Task 2: Standardize payment_method ----------
print("\nRaw payment_method values:", orders["payment_method"].unique())
print("Distinct raw values:", orders["payment_method"].nunique())  # 7

orders["payment_method"] = orders["payment_method"].str.strip().str.upper()
print("\nAfter standardizing:")
print(orders["payment_method"].value_counts())  # CARD 70, UPI 55, COD 55



# ---------- Task 3: Remove duplicate orders ----------
key_cols = ["customer_id", "product_id", "order_date", "quantity",
            "discount_pct", "payment_method", "rating", "returned"]

dup_mask = orders.duplicated(subset=key_cols, keep="first")
dropped = orders[dup_mask].copy()
print("\nDropped duplicate order_ids:", dropped["order_id"].tolist())
# ['O0176', 'O0177', 'O0178', 'O0179', 'O0180']

orders_dedup = orders[~dup_mask].copy()
print("orders_dedup.shape:", orders_dedup.shape)  # (175, 9)



# ---------- Task 4: Impute missing values ----------
print("\nMissing discount_pct:", orders_dedup["discount_pct"].isna().sum())  # 12
print("Missing rating:", orders_dedup["rating"].isna().sum())               # 15

rating_median = orders_dedup["rating"].median()
print("Rating median (before imputing):", rating_median)                    # 3.0

orders_clean = orders_dedup.copy()
orders_clean["discount_pct"] = orders_clean["discount_pct"].fillna(0)
orders_clean["rating"] = orders_clean["rating"].fillna(rating_median)

print("Nulls after imputing:")
print(orders_clean[["discount_pct", "rating"]].isnull().sum())  # both 0




# ---------- Task 5: Merge and reconcile ----------
def add_order_value(df):
    merged = (df.merge(products, on="product_id", how="left")
                .merge(customers, on="customer_id", how="left"))
    merged["order_value"] = (merged["quantity"] * merged["price"]
                             * (1 - merged["discount_pct"] / 100))
    return merged

clean = add_order_value(orders_clean)
cleaned_total = round(clean["order_value"].sum(), 2)
print("\nCleaned total order_value (175 rows):", cleaned_total)  # 97358.30

# Raw total: all 180 rows, with the same NULL-discount rule (0%)
raw_total = round(add_order_value(
    orders.assign(discount_pct=orders["discount_pct"].fillna(0)))["order_value"].sum(), 2)
print("Raw total order_value (180 rows):", raw_total)  # 99860.20

# Independent check: value of the 5 dropped rows
dropped_value = round(add_order_value(dropped)["order_value"].sum(), 2)
print("Order value of the 5 dropped duplicates:", dropped_value)  # 2501.90

delta = round(raw_total - cleaned_total, 2)
assert delta == dropped_value, "Reconciliation does not balance"

print(
    f"\nReconciliation: raw revenue is {raw_total:,.2f} and cleaned revenue is "
    f"{cleaned_total:,.2f}. The difference of {delta:,.2f} is exactly the combined "
    f"order value of the 5 duplicate rows removed in Task 3 (O0176-O0180), which "
    f"were double submissions. Imputing discount_pct and rating does not change "
    f"any order_value, so it accounts for none of this difference."
)




# ---------- Task 6: IQR outlier detection ----------
q1 = clean["quantity"].quantile(0.25)
q3 = clean["quantity"].quantile(0.75)
iqr = q3 - q1
lower = q1 - 1.5 * iqr
upper = q3 + 1.5 * iqr
print(f"\nQ1={q1}, Q3={q3}, IQR={iqr}, lower={lower}, upper={upper}")
# Q1=1.0, Q3=2.0, IQR=1.0, lower=-0.5, upper=3.5

clean["is_outlier"] = ~clean["quantity"].between(lower, upper)
print("Outlier rows:")
print(clean.loc[clean["is_outlier"], ["order_id", "quantity"]])  # O0011 (25), O0098 (30)



# ---------- Task 7: Hypothesis - COD has a higher return rate ----------
print("\nHYPOTHESIS: COD orders have a higher return rate than Card or UPI.")
pay = clean.groupby("payment_method")["returned"].agg(["count", "mean"])
pay["return_rate_pct"] = (pay["mean"] * 100).round(1)
print(pay)  # CARD 14.7, COD 44.4, UPI 18.9
print("Result: Confirmed")



# ---------- Task 8: Multi-level segmentation ----------
seg = clean.groupby(["payment_method", "city_tier"])["returned"].agg(["count", "mean"])
seg["return_rate_pct"] = (seg["mean"] * 100).round(1)
print("\nReturn rate by payment method and city tier:")
print(seg)

worst = seg["return_rate_pct"].idxmax()
print(f"Highest-risk segment: {worst[0]} in Tier {worst[1]} cities, "
      f"{seg.loc[worst, 'return_rate_pct']}% return rate")  # COD, Tier 2, 54.5%



# ---------- Task 9: Correlation analysis ----------
def band(r):
    r = abs(r)
    if r < 0.2: return "negligible"
    if r < 0.4: return "weak"
    if r < 0.7: return "moderate"
    return "strong"

cols = ["rating", "returned", "discount_pct", "quantity"]
corr = clean[cols].corr().round(2)
print("\nCorrelation matrix:")
print(corr)

print("\nPairwise bands:")
for i, a in enumerate(cols):
    for b in cols[i + 1:]:
        r = corr.loc[a, b]
        print(f"  {a} vs {b}: r={r} ({band(r)})")

print("Hypothesis 'higher discounts reduce returns': Busted "
      f"(discount_pct vs returned r={corr.loc['discount_pct', 'returned']})")



# ---------- Task 10: Outlier-corrected time series ----------
clean["order_date"] = pd.to_datetime(clean["order_date"])
clean["year_month"] = clean["order_date"].dt.to_period("M").astype(str)

monthly_all = clean.groupby("year_month")["order_value"].sum().round(2)
monthly_corr = (clean[~clean["is_outlier"]]
                .groupby("year_month")["order_value"].sum().round(2))

print("\nMonthly revenue INCLUDING outliers:")
print(monthly_all)
print("\nMonthly revenue EXCLUDING outliers:")
print(monthly_corr)

print("\nNOTE: January looks like the peak only because two bulk orders, O0011 "
      "(2026-01-28) and O0098 (2026-01-10), land in January. After excluding them, "
      "March (20318.90) is the true peak month.")



# ---------- Export findings.json for narrator/ ----------
seg_pm, seg_tier = worst
peak_month = monthly_corr.idxmax()
inflated_month = monthly_all.idxmax()

findings = {
    "cleaned_total_revenue_inr": cleaned_total,
    "raw_total_revenue_inr": raw_total,
    "duplicate_reconciliation_delta_inr": delta,
    "return_rate_by_payment": {k: float(v) for k, v in pay["return_rate_pct"].items()},
    "highest_risk_segment": {
        "payment_method": seg_pm,
        "city_tier": int(seg_tier),
        "return_rate_pct": float(seg.loc[worst, "return_rate_pct"]),
    },
    "true_peak_month": {
        "month": peak_month,
        "revenue_inr": float(monthly_corr.max()),
    },
    "outlier_inflated_month": {
        "month": inflated_month,
        "apparent_revenue_inr": float(monthly_all.max()),
        "corrected_revenue_inr": float(monthly_corr[inflated_month]),
    },
    # Extra key so visualize.py can draw the corrected trend without re-running the analysis
    "monthly_revenue_corrected_inr": {m: float(v) for m, v in monthly_corr.items()},
}

FINDINGS_PATH.parent.mkdir(exist_ok=True)
with open(FINDINGS_PATH, "w") as f:
    json.dump(findings, f, indent=2)
print(f"\nWrote {FINDINGS_PATH}")