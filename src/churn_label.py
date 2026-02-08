from pathlib import Path
import argparse
import pandas as pd
import numpy as np


def to_clean_id(s: pd.Series) -> pd.Series:
    return s.astype(str).str.replace(".0", "", regex=False).str.strip()


def normalize_date(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce").dt.normalize()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tx", required=True, help="transactions_clean.csv")
    ap.add_argument("--features", required=True, help="customer_features_monthly.csv")
    ap.add_argument("--out", required=True)
    ap.add_argument("--label_window_days", type=int, default=90)
    ap.add_argument("--require_active_in_lookback", action="store_true",
                    help="Only keep customers active in lookback features")
    args = ap.parse_args()

    tx = pd.read_csv(args.tx)
    tx["InvoiceDate"] = pd.to_datetime(tx["InvoiceDate"], errors="coerce")
    tx = tx.dropna(subset=["InvoiceDate", "CustomerID", "InvoiceNo"]).copy()
    tx["CustomerID"] = to_clean_id(tx["CustomerID"])
    tx["InvoiceDate"] = tx["InvoiceDate"].dt.normalize()

    feats = pd.read_csv(args.features)
    feats["SnapshotDate"] = normalize_date(feats["SnapshotDate"])
    feats["CustomerID"] = to_clean_id(feats["CustomerID"])
    feats = feats.dropna(subset=["SnapshotDate", "CustomerID"]).copy()

    global_max_tx = tx["InvoiceDate"].max()
    if pd.isna(global_max_tx):
        raise ValueError("No valid InvoiceDate found in transactions.")

    labels = []
    for snap, chunk in feats.groupby("SnapshotDate", sort=True):
        window_end = snap + pd.Timedelta(days=args.label_window_days)
        if window_end > global_max_tx:
            labels.append(
                pd.DataFrame({
                    "CustomerID": chunk["CustomerID"].tolist(),
                    "SnapshotDate": snap,
                    "churn_label": np.nan
                })
            )
            continue

        start = snap + pd.Timedelta(days=1)
        end = window_end

        in_window = tx[(tx["InvoiceDate"] >= start) & (tx["InvoiceDate"] <= end)]
        buyers = set(in_window["CustomerID"].unique())

        cids = chunk["CustomerID"].tolist()
        churn = [0 if cid in buyers else 1 for cid in cids]
        labels.append(pd.DataFrame({"CustomerID": cids, "SnapshotDate": snap, "churn_label": churn}))

    lab = pd.concat(labels, ignore_index=True)
    out = feats.merge(lab, on=["CustomerID", "SnapshotDate"], how="left")

    if args.require_active_in_lookback:
        if "total_orders" in out.columns:
            out = out[out["total_orders"].fillna(0) > 0].copy()

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)

    n_total = len(out)
    n_labeled = int(out["churn_label"].notna().sum())
    n_unobs = n_total - n_labeled
    months = out["SnapshotDate"].nunique()

    print(
        f"✅ Saved labeled snapshots: {args.out} | Rows: {n_total:,} | Months: {months} | "
        f"Labeled: {n_labeled:,} | Unobservable (NaN): {n_unobs:,} | "
        f"Global max tx date: {global_max_tx.date()}"
    )


if __name__ == "__main__":
    main()
