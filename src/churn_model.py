from pathlib import Path
import argparse
import pandas as pd
import numpy as np

from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.linear_model import LogisticRegression

try:
    from lightgbm import LGBMClassifier
    HAS_LGBM = True
except Exception:
    HAS_LGBM = False


FEATURE_CANDIDATES = [
    "tenure_days",
    "total_orders",
    "total_revenue",
    "avg_basket_value",
    "avg_items_per_order",
    "avg_unique_skus",
    "avg_days_between_orders",
    "median_days_between_orders",
    "recency_days",
    "revenue_last_30d",
    "orders_last_30d",
    "revenue_last_90d",
    "orders_last_90d",
]


def bucket_risk(p: float) -> str:
    if p >= 0.80:
        return "High"
    if p >= 0.50:
        return "Medium"
    return "Low"


def to_clean_id(s: pd.Series) -> pd.Series:
    return s.astype(str).str.replace(".0", "", regex=False).str.strip()


def normalize_date(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce").dt.normalize()


def choose_cutoff_date(df: pd.DataFrame, cutoff_arg: str | None) -> pd.Timestamp:
    """
    Time-based holdout. If cutoff is provided, use it.
    Otherwise, use last 3 distinct snapshot months as test.
    """
    df = df.sort_values("SnapshotDate")
    if cutoff_arg:
        cutoff = pd.to_datetime(cutoff_arg, errors="coerce")
        if pd.isna(cutoff):
            raise ValueError(f"Invalid --cutoff_date: {cutoff_arg}")
        return cutoff.normalize()

    months = sorted(df["SnapshotDate"].dt.to_period("M").unique())
    if len(months) <= 3:
        last_month = months[-1]
        cutoff = df[df["SnapshotDate"].dt.to_period("M") == last_month]["SnapshotDate"].min()
        return pd.to_datetime(cutoff).normalize()

    last_months = months[-3:]
    cutoff = df[df["SnapshotDate"].dt.to_period("M").isin(last_months)]["SnapshotDate"].min()
    return pd.to_datetime(cutoff).normalize()


def dynamic_threshold(row: pd.Series) -> float:
    """
    Non-circular decision threshold:
    - Prefer value_tier / segment if present
    - else single default threshold (0.50)
    """
    seg = str(row.get("segment", row.get("Segment", ""))).strip()
    tier = str(row.get("value_tier", row.get("ValueTier", ""))).strip()

    if tier:
        t = tier.lower()
        if t.startswith("high"):
            return 0.30
        if t.startswith("mid"):
            return 0.50
        if t.startswith("low"):
            return 0.70

    if seg:
        seg_l = seg.lower()
        if seg_l in ["champions", "loyal"]:
            return 0.30
        if seg_l in ["potential loyalist", "promising", "new customers", "needs attention"]:
            return 0.50
        if seg_l in ["at risk", "hibernating", "lost", "about to sleep"]:
            return 0.70

    return 0.50


def add_action_flag_top_percent(scores: pd.DataFrame, top_pct: float = 0.15) -> pd.DataFrame:
    """
    Add action_flag_topXX within each SnapshotDate.
    Prioritize expected_loss if present, else churn_probability.
    """
    flag_col = f"action_flag_top{int(top_pct*100)}"
    metric = "expected_loss" if "expected_loss" in scores.columns else "churn_probability"

    def _flag(g: pd.DataFrame) -> pd.DataFrame:
        g = g.copy()
        # rank descending
        g["_rank"] = g[metric].rank(method="first", ascending=False)
        cutoff = int(np.ceil(len(g) * top_pct))
        cutoff = max(cutoff, 1)
        g[flag_col] = (g["_rank"] <= cutoff).astype(int)
        return g.drop(columns=["_rank"])

    return scores.groupby("SnapshotDate", group_keys=False).apply(_flag)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True, help="customer_features_labeled.csv")
    ap.add_argument("--segment_snapshot", default=None, help="customer_segment_snapshot.csv (optional)")
    ap.add_argument("--out_scores", required=True)
    ap.add_argument("--out_report", required=True)
    ap.add_argument("--cutoff_date", default=None, help="YYYY-MM-DD for time split. If empty, uses last 3 months as test.")
    args = ap.parse_args()

    # -------------------------
    # Load & normalize base df (KEEP unlabeled rows for scoring)
    # -------------------------
    df = pd.read_csv(args.in_path)

    if "SnapshotDate" not in df.columns:
        raise ValueError("Missing SnapshotDate in features-labeled input.")
    df["SnapshotDate"] = normalize_date(df["SnapshotDate"])

    if "CustomerID" not in df.columns:
        raise ValueError("Missing CustomerID in features-labeled input.")
    df["CustomerID"] = to_clean_id(df["CustomerID"])

    if "churn_label" not in df.columns:
        raise ValueError("Missing churn_label in features-labeled input.")

    df = df.dropna(subset=["SnapshotDate", "CustomerID"]).copy()

    # -------------------------
    # SORT FIRST (alignment)
    # -------------------------
    df = df.sort_values("SnapshotDate").reset_index(drop=True)

    # -------------------------
    # Feature selection + clean (ALL rows for scoring)
    # -------------------------
    feats = [c for c in FEATURE_CANDIDATES if c in df.columns]
    if not feats:
        raise ValueError("No candidate features found in input. Check your feature_engineering output.")

    X_all = df[feats].copy()
    X_all = X_all.replace([np.inf, -np.inf], np.nan).fillna(0)

    # labeled subset for training/evaluation
    labeled_mask = df["churn_label"].notna()
    df_lab = df.loc[labeled_mask].copy()
    X_lab = X_all.loc[labeled_mask].copy()
    y = df_lab["churn_label"].astype(int).values

    if len(df_lab) < 100:
        raise ValueError("Too few labeled rows after right-censoring. Check churn_label.py window and dataset max date.")

    # -------------------------
    # Time-based split (on labeled rows)
    # -------------------------
    cutoff = choose_cutoff_date(df_lab, args.cutoff_date)
    train_idx = df_lab["SnapshotDate"] < cutoff
    test_idx = ~train_idx

    if len(np.unique(y[test_idx.values])) < 2:
        last_month = df_lab["SnapshotDate"].dt.to_period("M").max()
        cutoff = df_lab[df_lab["SnapshotDate"].dt.to_period("M") == last_month]["SnapshotDate"].min()
        cutoff = pd.to_datetime(cutoff).normalize()
        train_idx = df_lab["SnapshotDate"] < cutoff
        test_idx = ~train_idx

    X_train, y_train = X_lab.loc[train_idx], y[train_idx.values]
    X_test, y_test = X_lab.loc[test_idx], y[test_idx.values]

    # -------------------------
    # Models
    # -------------------------
    lr = LogisticRegression(max_iter=5000)
    lr.fit(X_train, y_train)
    lr_proba = lr.predict_proba(X_test)[:, 1]
    lr_auc = roc_auc_score(y_test, lr_proba)
    lr_ap = average_precision_score(y_test, lr_proba)

    best_model = lr
    best_name = "LogReg"
    best_auc = lr_auc
    best_ap = lr_ap

    lgbm_auc = None
    lgbm_ap = None

    if HAS_LGBM:
        lgbm = LGBMClassifier(
            random_state=42,
            n_estimators=300,
            learning_rate=0.05,
            num_leaves=31,
            min_child_samples=200,
            subsample=0.8,
            subsample_freq=1,
            colsample_bytree=0.8,
        )
        lgbm.fit(X_train, y_train)
        lgbm_proba = lgbm.predict_proba(X_test)[:, 1]
        lgbm_auc = roc_auc_score(y_test, lgbm_proba)
        lgbm_ap = average_precision_score(y_test, lgbm_proba)

        if (lgbm_auc > best_auc) or (np.isclose(lgbm_auc, best_auc) and lgbm_ap >= best_ap):
            best_model = lgbm
            best_name = "LightGBM"
            best_auc = lgbm_auc
            best_ap = lgbm_ap

    # -------------------------
    # Report (labeled only)
    # -------------------------
    pos_rate_train = float(np.mean(y_train)) if len(y_train) else float("nan")
    pos_rate_test = float(np.mean(y_test)) if len(y_test) else float("nan")

    report_lines = [
        f"Cutoff date (test starts): {cutoff.date()}",
        f"Train rows (labeled): {len(X_train):,} | Test rows (labeled): {len(X_test):,}",
        f"Churn rate train: {pos_rate_train:.4f} | test: {pos_rate_test:.4f}",
        f"LogReg ROC-AUC: {lr_auc:.4f} | PR-AUC: {lr_ap:.4f}",
    ]
    if HAS_LGBM:
        report_lines.append(f"LightGBM ROC-AUC: {lgbm_auc:.4f} | PR-AUC: {lgbm_ap:.4f}")
    else:
        report_lines.append("LightGBM not installed (pip install lightgbm).")

    report_lines += [
        f"Selected model: {best_name}",
        f"Features ({len(feats)}): {feats}",
        f"Total rows scored (incl. unlabeled): {len(df):,}",
        f"Rows labeled for training/eval: {int(labeled_mask.sum()):,} | Unlabeled (unobservable): {int((~labeled_mask).sum()):,}",
    ]

    Path(args.out_report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_report).write_text("\n".join(report_lines), encoding="utf-8")

    # -------------------------
    # Score ALL rows (incl unlabeled)
    # -------------------------
    proba_all = best_model.predict_proba(X_all)[:, 1]

    scores = df[["CustomerID", "SnapshotDate"]].copy()
    scores["CustomerID"] = to_clean_id(scores["CustomerID"])
    scores["SnapshotDate"] = normalize_date(scores["SnapshotDate"])

    # keep churn_label as-is (can be NaN for unobservable snapshots)
    scores["churn_label"] = df["churn_label"]
    scores["churn_probability"] = proba_all
    scores["risk_bucket"] = scores["churn_probability"].apply(bucket_risk)

    # carry BI-friendly columns
    keep_cols = ["total_revenue", "total_orders", "recency_days", "tenure_days"]
    for c in keep_cols:
        if c in df.columns:
            scores[c] = df[c].values

    # -------------------------
    # Segment join (optional)
    # -------------------------
    if args.segment_snapshot:
        seg = pd.read_csv(args.segment_snapshot)
        if "SnapshotDate" not in seg.columns or "CustomerID" not in seg.columns:
            raise ValueError("segment_snapshot must contain CustomerID and SnapshotDate.")
        seg["SnapshotDate"] = normalize_date(seg["SnapshotDate"])
        seg["CustomerID"] = to_clean_id(seg["CustomerID"])

        join_cols = [c for c in seg.columns if c not in ["CustomerID", "SnapshotDate"]]
        scores = scores.merge(
            seg[["CustomerID", "SnapshotDate"] + join_cols],
            on=["CustomerID", "SnapshotDate"],
            how="left",
        )

        # alias for decisioning robustness (do NOT remove original BI columns)
        if "Segment" in scores.columns and "segment" not in scores.columns:
            scores["segment"] = scores["Segment"]
        if "RecencyDays" in scores.columns and "recency_days" not in scores.columns:
            scores["recency_days"] = scores["RecencyDays"]

    # -------------------------
    # Decisioning + Action targeting
    # -------------------------
    scores["dynamic_threshold"] = scores.apply(dynamic_threshold, axis=1)
    scores["churn_flag"] = (scores["churn_probability"] >= scores["dynamic_threshold"]).astype(int)

    # expected_loss proxy (keeps dashboard stable even if column missing)
    if "total_revenue" in scores.columns:
        scores["expected_loss"] = scores["churn_probability"] * scores["total_revenue"].fillna(0)
    else:
        scores["expected_loss"] = scores["churn_probability"]

    # action list: top 15% within each snapshot
    scores = add_action_flag_top_percent(scores, top_pct=0.15)

    Path(args.out_scores).parent.mkdir(parents=True, exist_ok=True)
    scores.to_csv(args.out_scores, index=False)
    print(f"✅ Saved scores: {args.out_scores} | Rows: {len(scores):,} | Model: {best_name}")


if __name__ == "__main__":
    main()
