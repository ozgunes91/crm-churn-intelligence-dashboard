# segment_snapshot.py
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd
import numpy as np


def to_clean_id(s: pd.Series) -> pd.Series:
    return s.astype(str).str.replace(".0", "", regex=False).str.strip()


def _safe_to_datetime(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce", utc=False)


def month_ends_between(start: pd.Timestamp, end: pd.Timestamp) -> list[pd.Timestamp]:
    start = pd.Timestamp(start).normalize()
    end = pd.Timestamp(end).normalize()
    first = (start + pd.offsets.MonthEnd(0))
    if first < start:
        first = start + pd.offsets.MonthEnd(1)
    month_ends = pd.date_range(first, end + pd.offsets.MonthEnd(0), freq="ME")
    return [pd.Timestamp(d).normalize() for d in month_ends]


def rfm_scores_quantile(rfm: pd.DataFrame) -> pd.DataFrame:
    out = rfm.copy()

    def qscore(series: pd.Series, ascending: bool) -> pd.Series:
        s = series.replace([np.inf, -np.inf], np.nan).fillna(0)
        ranks = s.rank(method="first", ascending=ascending)
        try:
            bins = pd.qcut(ranks, 5, labels=[1, 2, 3, 4, 5])
            return bins.astype(int)
        except ValueError:
            bins = pd.cut(ranks, 5, labels=[1, 2, 3, 4, 5], include_lowest=True)
            return bins.astype(int)

    out["R_Score"] = qscore(out["RecencyDays"], ascending=True)
    out["R_Score"] = 6 - out["R_Score"]

    out["F_Score"] = qscore(out["Frequency"], ascending=True)
    out["M_Score"] = qscore(out["Monetary"], ascending=True)

    out["RFM_Score"] = out["R_Score"] + out["F_Score"] + out["M_Score"]
    return out


def segment_from_rfm(r: int, f: int, m: int) -> str:
    """
    Corporate RFM segmentation (9 segments).
    Assumes r,f,m are 1..5 where 5 is best.
    """

    # 1) Champions: very recent + very frequent + high value
    if r >= 4 and f >= 4 and m >= 4:
        return "Champions"

    # 2) Loyal: very recent + frequent (value can vary)
    if r >= 4 and f >= 4:
        return "Loyal"

    # 3) New Customers: very recent + first-time (or near-first) + usually low/med value
    # Strict "new" = f==1 (recommended)
    if r >= 4 and f == 1:
        return "New Customers"

    # 4) Potential Loyalist: recent and already repeating OR recent, decent value
    # (these are your “convert to loyal” customers)
    if r >= 4 and f in (2, 3):
        return "Potential Loyalist"

    # 5) Promising: fairly recent but low frequency/value yet
    if r == 3 and f <= 2:
        return "Promising"

    # 6) Needs Attention: mid recency but decent frequency or value (still recoverable)
    if r == 3 and (f >= 3 or m >= 4):
        return "Needs Attention"

    # 7) About To Sleep: getting old + low frequency/value
    if r == 2 and f <= 2 and m <= 3:
        return "About To Sleep"

    # 8) At Risk: old/inactive but was valuable or frequent (priority winback)
    # key corporate tweak: HIGH M or HIGH F -> At Risk instead of Lost
    if r <= 2 and (m >= 4 or f >= 3):
        return "At Risk"

    # 9) Lost: old + low frequency + low value
    return "Lost"


def compute_snapshot_rfm(
    tx: pd.DataFrame,
    snapshot_end: pd.Timestamp,
    customer_col: str = "CustomerID",
    date_col: str = "InvoiceDate",
    invoice_col: str = "InvoiceNo",
    amount_col: str = "TotalPrice",
) -> pd.DataFrame:
    snap_end = pd.Timestamp(snapshot_end).normalize()
    ref_date = snap_end + pd.Timedelta(days=1)

    sub = tx.loc[tx[date_col] <= snap_end].copy()
    if sub.empty:
        return pd.DataFrame(columns=[
            customer_col, "SnapshotDate", "YearMonth",
            "RecencyDays", "Frequency", "Monetary",
            "R_Score", "F_Score", "M_Score", "RFM_Score", "Segment"
        ])

    grp = sub.groupby(customer_col, as_index=False).agg(
        LastPurchase=(date_col, "max"),
        FirstPurchase=(date_col, "min"),
        Frequency=(invoice_col, pd.Series.nunique),
        Monetary=(amount_col, "sum"),
    )

    grp["RecencyDays"] = (ref_date - grp["LastPurchase"]).dt.days.clip(lower=0)
    grp["Frequency"] = grp["Frequency"].fillna(0).astype(int)
    grp["Monetary"] = grp["Monetary"].fillna(0.0)

    scored = rfm_scores_quantile(grp[[customer_col, "RecencyDays", "Frequency", "Monetary"]])
    scored["Segment"] = [
        segment_from_rfm(int(r), int(f), int(m))
        for r, f, m in zip(scored["R_Score"], scored["F_Score"], scored["M_Score"])
    ]

    scored["SnapshotDate"] = snap_end
    scored["YearMonth"] = scored["SnapshotDate"].dt.strftime("%Y-%m")

    cols = [
        customer_col, "SnapshotDate", "YearMonth",
        "RecencyDays", "Frequency", "Monetary",
        "R_Score", "F_Score", "M_Score", "RFM_Score",
        "Segment"
    ]
    return scored[cols].sort_values([customer_col]).reset_index(drop=True)


def build_segment_snapshot(in_path: Path, out_path: Path, start: str | None = None, end: str | None = None) -> None:
    tx = pd.read_csv(in_path)

    required = {"InvoiceDate", "CustomerID", "InvoiceNo"}
    missing = required - set(tx.columns)
    if missing:
        raise ValueError(f"Missing required columns in transactions: {sorted(missing)}")

    if "TotalPrice" not in tx.columns:
        if {"Quantity", "UnitPrice"}.issubset(tx.columns):
            tx["TotalPrice"] = tx["Quantity"] * tx["UnitPrice"]
        else:
            raise ValueError("No TotalPrice column found (and cannot derive from Quantity*UnitPrice).")

    tx["InvoiceDate"] = _safe_to_datetime(tx["InvoiceDate"]).dt.tz_localize(None)
    tx = tx.dropna(subset=["InvoiceDate", "CustomerID"]).copy()

    tx["CustomerID"] = to_clean_id(tx["CustomerID"])

    min_d = tx["InvoiceDate"].min().normalize()
    max_d = tx["InvoiceDate"].max().normalize()

    if start:
        min_d = max(pd.Timestamp(start).normalize(), min_d)
    if end:
        max_d = min(pd.Timestamp(end).normalize(), max_d)

    month_ends = month_ends_between(min_d, max_d)
    if not month_ends:
        raise ValueError("No month-ends found in the specified date range.")

    snapshots = [compute_snapshot_rfm(tx, me) for me in month_ends]
    out = pd.concat(snapshots, ignore_index=True)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    print(f"✅ Segment snapshot saved: {out_path}")
    print(f"📌 Rows: {len(out):,} | Months: {len(month_ends)} | Unique customers: {out['CustomerID'].nunique():,}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True)
    ap.add_argument("--out", dest="out_path", required=True)
    ap.add_argument("--start", default=None)
    ap.add_argument("--end", default=None)
    args = ap.parse_args()

    build_segment_snapshot(Path(args.in_path), Path(args.out_path), start=args.start, end=args.end)


if __name__ == "__main__":
    main()
