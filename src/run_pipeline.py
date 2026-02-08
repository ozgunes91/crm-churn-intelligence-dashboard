from pathlib import Path
import subprocess
import pandas as pd
import sys

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PROC = DATA / "processed"

SCRIPTS = {
    "make_dataset": ROOT / "src" / "make_dataset.py",
    "feature_engineering": ROOT / "src" / "feature_engineering.py",
    "churn_label": ROOT / "src" / "churn_label.py",
    "segment_snapshot": ROOT / "src" / "segment_snapshot.py",
    "churn_model": ROOT / "src" / "churn_model.py",
    "campaign_actions": ROOT / "src" / "campaign_actions.py",
}


def run(cmd: list[str]):
    if cmd[0] == "python":
        cmd = [sys.executable] + cmd[1:]
    print("▶", " ".join(cmd))
    subprocess.check_call(cmd)


def main():
    PROC.mkdir(parents=True, exist_ok=True)

    tx_clean = PROC / "transactions_clean.csv"
    feats = PROC / "customer_features_monthly.csv"
    feats_labeled = PROC / "customer_features_labeled.csv"
    seg_snap = PROC / "customer_segment_snapshot.csv"
    churn_scores = PROC / "churn_scores.csv"
    churn_report = PROC / "churn_model_report.txt"
    actions = PROC / "campaign_actions.csv"

    # 1) Clean transactions
    run(["python", str(SCRIPTS["make_dataset"])])

    # 2) Monthly features
    run([
        "python", str(SCRIPTS["feature_engineering"]),
        "--in", str(tx_clean),
        "--out", str(feats),
        "--lookback_days", "365"
    ])

    # 3) Labels (right-censoring)
    run([
        "python", str(SCRIPTS["churn_label"]),
        "--tx", str(tx_clean),
        "--features", str(feats),
        "--out", str(feats_labeled),
        "--label_window_days", "90"
    ])

    # 4) Segment snapshot (time-aware)
    run([
        "python", str(SCRIPTS["segment_snapshot"]),
        "--in", str(tx_clean),
        "--out", str(seg_snap)
    ])

    # 5) Churn model scores (HISTORY)
    run([
        "python", str(SCRIPTS["churn_model"]),
        "--in", str(feats_labeled),
        "--segment_snapshot", str(seg_snap),
        "--out_scores", str(churn_scores),
        "--out_report", str(churn_report)
    ])

    # 6) Campaign actions (HISTORY) — recommended: only_action_list in BI would be a separate extract;
    # keep history full by default
    run([
        "python", str(SCRIPTS["campaign_actions"]),
        "--scores", str(churn_scores),
        "--out", str(actions)
    ])

    # 7) Export LATEST extracts for BI convenience
    df_scores = pd.read_csv(churn_scores)
    df_scores["SnapshotDate"] = pd.to_datetime(df_scores["SnapshotDate"], errors="coerce")
    latest = df_scores["SnapshotDate"].max()

    df_scores_latest = df_scores[df_scores["SnapshotDate"] == latest].copy()
    out_scores_latest = PROC / "churn_scores_latest.csv"
    df_scores_latest.to_csv(out_scores_latest, index=False)

    df_act = pd.read_csv(actions)
    df_act["SnapshotDate"] = pd.to_datetime(df_act["SnapshotDate"], errors="coerce")
    df_act_latest = df_act[df_act["SnapshotDate"] == latest].copy()
    out_actions_latest = PROC / "campaign_actions_latest.csv"
    df_act_latest.to_csv(out_actions_latest, index=False)

    # Optional: also export action list only (top15) for ops
    if "action_flag_top15" in df_scores_latest.columns:
        df_ops = df_scores_latest[df_scores_latest["action_flag_top15"] == 1].copy()
        out_ops = PROC / "churn_ops_target_latest.csv"
        df_ops.to_csv(out_ops, index=False)
    else:
        out_ops = None

    print("\n✅ DONE")
    print(f"   churn_scores (history): {churn_scores}")
    print(f"   churn_scores (latest):  {out_scores_latest}")
    print(f"   actions (history):      {actions}")
    print(f"   actions (latest):       {out_actions_latest}")
    if out_ops:
        print(f"   ops target (latest):    {out_ops}")
    print(f"   latest SnapshotDate:    {latest.date()}")


if __name__ == "__main__":
    main()
