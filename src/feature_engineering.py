from pathlib import Path
import argparse
import pandas as pd
import numpy as np


def month_end_dates(first: pd.Timestamp, last: pd.Timestamp) -> pd.DatetimeIndex:
    first_me = (first + pd.offsets.MonthEnd(0))
    last_me = (last + pd.offsets.MonthEnd(0))
    return pd.date_range(first_me, last_me, freq="ME")


def _to_clean_id(s: pd.Series) -> pd.Series:
    return s.astype(str).str.replace(".0", "", regex=False).str.strip()


def build_features_asof(tx: pd.DataFrame, as_of: pd.Timestamp, lookback_days: int) -> pd.DataFrame:
    """
    As-of features (no leakage): use ONLY data <= as_of.

    Fix:
    - Lifetime metrics computed from full history (<= as_of).
    - Lookback only used for "behavioral" stats (avg basket, gaps).
    """
    as_of = pd.Timestamp(as_of).normalize()

    hist_all = tx[tx["InvoiceDate"] <= as_of].copy()
    if hist_all.empty:
        return pd.DataFrame(columns=["CustomerID", "SnapshotDate"])

    if lookback_days is not None and lookback_days > 0:
        start = as_of - pd.Timedelta(days=lookback_days)
        hist_lb = hist_all[hist_all["InvoiceDate"] >= start].copy()
    else:
        hist_lb = hist_all.copy()

    # -------------------------
    # Lifetime aggregates (correct tenure)
    # -------------------------
    g_all = hist_all.groupby("CustomerID", as_index=False)
    agg = g_all.agg(
        first_purchase=("InvoiceDate", "min"),
        last_purchase=("InvoiceDate", "max"),
        total_orders=("InvoiceNo", pd.Series.nunique),
        total_revenue=("TotalPrice", "sum"),
        total_items=("Quantity", "sum"),
        unique_skus=("StockCode", pd.Series.nunique) if "StockCode" in hist_all.columns else ("InvoiceNo", "size"),
    )

    agg["recency_days"] = (as_of - agg["last_purchase"]).dt.days
    agg["tenure_days"] = (agg["last_purchase"] - agg["first_purchase"]).dt.days

    # -------------------------
    # Lookback order-level stats (recent behavior)
    # -------------------------
    if hist_lb.empty:
        per_cust = agg[["CustomerID"]].copy()
        per_cust["avg_basket_value"] = np.nan
        per_cust["avg_items_per_order"] = np.nan
        per_cust["avg_unique_skus"] = np.nan
        gaps = agg[["CustomerID"]].copy()
        gaps["avg_days_between_orders"] = np.nan
        gaps["median_days_between_orders"] = np.nan
    else:
        order_level = hist_lb.groupby(["CustomerID", "InvoiceNo"], as_index=False).agg(
            order_revenue=("TotalPrice", "sum"),
            order_items=("Quantity", "sum"),
            order_unique_skus=("StockCode", pd.Series.nunique) if "StockCode" in hist_lb.columns else ("InvoiceNo", "size"),
            order_date=("InvoiceDate", "min"),
        )

        per_cust = order_level.groupby("CustomerID", as_index=False).agg(
            avg_basket_value=("order_revenue", "mean"),
            avg_items_per_order=("order_items", "mean"),
            avg_unique_skus=("order_unique_skus", "mean"),
        )

        order_level = order_level.sort_values(["CustomerID", "order_date"])
        order_level["prev_date"] = order_level.groupby("CustomerID")["order_date"].shift(1)
        order_level["days_between"] = (order_level["order_date"] - order_level["prev_date"]).dt.days
        gaps = order_level.dropna(subset=["days_between"]).groupby("CustomerID", as_index=False).agg(
            avg_days_between_orders=("days_between", "mean"),
            median_days_between_orders=("days_between", "median"),
        )

    # -------------------------
    # Rolling windows (as_of anchored)
    # -------------------------
    def rolling_metrics(days: int) -> pd.DataFrame:
        w = hist_all[hist_all["InvoiceDate"] > (as_of - pd.Timedelta(days=days))]
        if w.empty:
            return pd.DataFrame({"CustomerID": agg["CustomerID"], f"revenue_last_{days}d": 0.0, f"orders_last_{days}d": 0})
        gw = w.groupby("CustomerID", as_index=False).agg(
            revenue=("TotalPrice", "sum"),
            orders=("InvoiceNo", pd.Series.nunique),
        )
        return gw.rename(columns={"revenue": f"revenue_last_{days}d", "orders": f"orders_last_{days}d"})

    r30 = rolling_metrics(30)
    r90 = rolling_metrics(90)

    out = agg.merge(per_cust, on="CustomerID", how="left").merge(gaps, on="CustomerID", how="left")
    out = out.merge(r30, on="CustomerID", how="left").merge(r90, on="CustomerID", how="left")

    # Fill rolling NaNs
    for c in ["revenue_last_30d", "orders_last_30d", "revenue_last_90d", "orders_last_90d"]:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0.0)

    out["SnapshotDate"] = as_of
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True)
    ap.add_argument("--out", dest="out_path", required=True)
    ap.add_argument("--start", type=str, default=None, help="YYYY-MM-DD (optional)")
    ap.add_argument("--end", type=str, default=None, help="YYYY-MM-DD (optional)")
    ap.add_argument("--lookback_days", type=int, default=365)
    args = ap.parse_args()

    tx = pd.read_csv(args.in_path)
    tx["InvoiceDate"] = pd.to_datetime(tx["InvoiceDate"], errors="coerce")
    tx = tx.dropna(subset=["InvoiceDate", "CustomerID", "InvoiceNo"]).copy()

    tx["CustomerID"] = _to_clean_id(tx["CustomerID"])
    tx["TotalPrice"] = pd.to_numeric(tx["TotalPrice"], errors="coerce").fillna(0.0)
    tx["Quantity"] = pd.to_numeric(tx.get("Quantity", 0), errors="coerce").fillna(0.0)

    first = pd.to_datetime(args.start) if args.start else tx["InvoiceDate"].min()
    last = pd.to_datetime(args.end) if args.end else tx["InvoiceDate"].max()

    snaps = month_end_dates(first, last)

    frames = []
    for as_of in snaps:
        frames.append(build_features_asof(tx, as_of, lookback_days=args.lookback_days))

    out = pd.concat(frames, ignore_index=True)

    Path(args.out_path).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out_path, index=False)

    print(
        f"✅ Saved monthly features: {args.out_path} | Rows: {len(out):,} | "
        f"Months: {out['SnapshotDate'].nunique()} | Customers: {out['CustomerID'].nunique():,}"
    )


if __name__ == "__main__":
    main()
