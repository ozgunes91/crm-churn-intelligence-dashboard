from pathlib import Path
import argparse
import pandas as pd
import numpy as np


def to_clean_id(s: pd.Series) -> pd.Series:
    return s.astype(str).str.replace(".0", "", regex=False).str.strip()


def normalize_date(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce").dt.normalize()


def safe_num(x, default=0.0):
    try:
        if pd.isna(x):
            return default
        return float(x)
    except Exception:
        return default


def compute_value_tier(df: pd.DataFrame) -> pd.Series:
    if "value_tier" in df.columns and df["value_tier"].notna().any():
        return df["value_tier"].fillna("Unknown").astype(str)

    if "total_revenue" not in df.columns:
        return pd.Series(["Unknown"] * len(df), index=df.index)

    rev = pd.to_numeric(df["total_revenue"], errors="coerce").fillna(0)
    q1 = float(rev.quantile(0.33))
    q2 = float(rev.quantile(0.66))

    def tier(v):
        v = safe_num(v, 0.0)
        if v >= q2:
            return "High Value"
        if v >= q1:
            return "Mid Value"
        return "Low Value"

    return rev.apply(tier)


def compute_priority(row: pd.Series) -> str:
    churn_flag = int(safe_num(row.get("churn_flag", 0), 0))
    p = safe_num(row.get("churn_probability", 0), 0.0)
    tier = str(row.get("value_tier", "Unknown")).lower()
    seg = str(row.get("segment", row.get("Segment", ""))).lower()

    if churn_flag == 1:
        if "high" in tier or seg in ["champions", "loyal"]:
            return "P1"
        if "mid" in tier:
            return "P2"
        return "P3"

    if p >= 0.60 and ("high" in tier or seg in ["champions", "loyal"]):
        return "P2"

    return "P4"


def choose_action_offer_message(row: pd.Series) -> tuple[str, str, str]:
    p = safe_num(row.get("churn_probability", 0.0), 0.0)
    churn_flag = int(safe_num(row.get("churn_flag", 0), 0))
    tier = str(row.get("value_tier", "Unknown")).lower()
    seg = str(row.get("segment", row.get("Segment", ""))).strip()

    rec = safe_num(row.get("recency_days", row.get("RecencyDays", 0)), 0.0)
    orders = safe_num(row.get("total_orders", row.get("Frequency", 0)), 0.0)

    high_value = ("high" in tier) or (seg.lower() in ["champions", "loyal"])
    very_inactive = rec >= 180
    new_or_one_timer = orders <= 1

    if churn_flag == 1:
        if high_value:
            if very_inactive:
                return ("Win-back (1:1 outreach)", "Personalized discount (10–15%)", "We miss you + tailored picks")
            return ("Win-back (priority queue)", "Personalized voucher (10%)", "Exclusive comeback: curated bestsellers")

        if very_inactive:
            return ("Reactivation campaign", "Free shipping / limited-time voucher", "Limited-time comeback offer")
        if new_or_one_timer:
            return ("Second-purchase nudge", "Small voucher (5–10%)", "Complete your set / popular add-ons")

        return ("Re-engagement email", "Small voucher (5–10%)", "New arrivals + reminder")

    if p >= 0.60 and high_value:
        return ("Proactive retention", "Perks / early access", "VIP early access + tailored picks")
    if p >= 0.40:
        return ("Cross-sell / upsell", "Bundle offer", "Recommended bundles based on your history")

    return ("Growth nurture", "Content / recommendations", "New arrivals + personalized recommendations")


def budget_suggestion(row: pd.Series) -> float:
    tier = str(row.get("value_tier", "Unknown")).lower()
    revenue = safe_num(row.get("total_revenue", 0.0), 0.0)
    p = safe_num(row.get("churn_probability", 0.0), 0.0)
    prio = str(row.get("priority", "P4"))

    base = 0.03 * revenue

    if prio == "P1":
        base *= 1.5
    elif prio == "P2":
        base *= 1.2
    elif prio == "P3":
        base *= 1.0
    else:
        base *= 0.6

    base *= (0.8 + 0.4 * min(max(p, 0.0), 1.0))

    if "high" in tier:
        cap, floor = 500.0, 80.0
    elif "mid" in tier:
        cap, floor = 200.0, 25.0
    elif "low" in tier:
        cap, floor = 80.0, 10.0
    else:
        cap, floor = 150.0, 15.0

    if revenue <= 0:
        return float(floor)

    return float(min(cap, max(floor, base)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scores", required=True, help="churn_scores.csv")
    ap.add_argument("--out", required=True, help="campaign_actions.csv")
    ap.add_argument("--only_flagged", action="store_true", help="Keep only churn_flag=1 rows.")
    ap.add_argument("--only_action_list", action="store_true", help="Keep only action_flag_top15=1 rows (recommended).")
    args = ap.parse_args()

    df = pd.read_csv(args.scores)

    for col in ["CustomerID", "SnapshotDate", "churn_probability"]:
        if col not in df.columns:
            raise ValueError(f"Missing required column in scores: {col}")

    df["CustomerID"] = to_clean_id(df["CustomerID"])
    df["SnapshotDate"] = normalize_date(df["SnapshotDate"])

    # Robust aliases (do not remove originals)
    if "Segment" in df.columns and "segment" not in df.columns:
        df["segment"] = df["Segment"]
    if "RecencyDays" in df.columns and "recency_days" not in df.columns:
        df["recency_days"] = df["RecencyDays"]

    if "risk_bucket" not in df.columns:
        df["risk_bucket"] = pd.cut(
            pd.to_numeric(df["churn_probability"], errors="coerce").fillna(0),
            bins=[-1, 0.5, 0.8, 2],
            labels=["Low", "Medium", "High"]
        ).astype(str)

    if "dynamic_threshold" not in df.columns:
        def rb_thr(rb):
            rb = str(rb).lower()
            if rb == "high":
                return 0.30
            if rb == "medium":
                return 0.50
            return 0.70
        df["dynamic_threshold"] = df["risk_bucket"].apply(rb_thr)

    if "churn_flag" not in df.columns:
        df["churn_flag"] = (
            pd.to_numeric(df["churn_probability"], errors="coerce").fillna(0) >=
            pd.to_numeric(df["dynamic_threshold"], errors="coerce").fillna(0.5)
        ).astype(int)

    df["value_tier"] = compute_value_tier(df)
    df["priority"] = df.apply(compute_priority, axis=1)

    triples = df.apply(choose_action_offer_message, axis=1)
    df["action"] = [t[0] for t in triples]
    df["offer_type"] = [t[1] for t in triples]
    df["message_angle"] = [t[2] for t in triples]

    df["budget_suggestion"] = df.apply(budget_suggestion, axis=1).round(2)

    if args.only_action_list:
        if "action_flag_top15" not in df.columns:
            raise ValueError("action_flag_top15 not found in scores. Run churn_model.py first.")
        df = df[df["action_flag_top15"] == 1].copy()

    if args.only_flagged:
        df = df[df["churn_flag"] == 1].copy()

    out_cols = [
        "CustomerID", "SnapshotDate",
        "churn_label", "churn_probability", "risk_bucket",
        "dynamic_threshold", "churn_flag",
        "expected_loss", "action_flag_top15",
        "total_revenue", "total_orders", "recency_days", "tenure_days",
        "segment", "RFM_Score", "value_tier",
        "priority", "action", "offer_type", "message_angle", "budget_suggestion"
    ]
    out_cols = [c for c in out_cols if c in df.columns]

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    df[out_cols].to_csv(args.out, index=False)
    print(f"✅ Saved campaign actions: {args.out} | Rows: {len(df):,}")


if __name__ == "__main__":
    main()
