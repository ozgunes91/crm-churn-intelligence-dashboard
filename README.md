# CRM Churn Intelligence Dashboard (Power BI + Python)

A portfolio-grade CRM analytics demo that unifies **sales performance**, **churn risk intelligence**, and a **capacity-aware retention action playbook** in a single Power BI report.

This project is built on the **Online Retail II** dataset and is intentionally designed as a **Data Science + BI** solution:
- **Python**: feature engineering, churn risk modeling, scoring, snapshot tables, and action list generation
- **Power BI + DAX**: semantic modeling, snapshot-aware KPIs, executive storytelling, and interactive exploration

---

## 📌 Live Demo & Assets
- **Interactive demo (Power BI Service / Publish to web):** `<DEMO_LINK>`
- **Repository:** `<GITHUB_LINK>`

> The demo is fully interactive (pages + slicers). If refresh is disabled in the service, the report still works as a static snapshot demo.

---

## Screenshots (Report Pages)
> Place the exported images under `assets/` and keep the same filenames.

| Page | Preview |
|---|---|
| Start Here | ![Start Here](assets/00-Start%20Here.png) |
| Executive Overview | ![Executive Overview](assets/01-Executive%20Overview.png) |
| Sales Performance | ![Sales Performance](assets/02-Sales%20Performance.png) |
| Customer Base & Segmentation | ![Customer Base & Segmentation](assets/03-Customer%20Base%20%26%20Segmentation.png) |
| Churn & Risk | ![Churn & Risk](assets/04-Churn%20%26%20Risk.png) |
| Action Playbook | ![Action Playbook](assets/05-Action%20Playbook.png) |
| Cohort & Retention | ![Cohort & Retention](assets/06-Cohort%20%26%20Retention.png) |
| Customer 360 | ![Customer 360](assets/07-Customer%20360.png) |

---

## What Makes This Report “Real-World”
### Two timelines, zero KPI confusion
This report explicitly separates **two time contexts** to avoid mixing definitions:

- **Sales Period (InvoiceDate)** → realized sales KPIs (Revenue, Orders, AOV, trends)
- **Snapshot (As-Of Date)** → churn risk / segmentation / expected loss / actions at a decision point

This is the backbone of the dashboard. Sales metrics never accidentally inherit snapshot logic (and vice versa).

---

## Pages & What They Answer
1. **Start Here**  
   Definitions and usage: Sales Period vs Snapshot (As-Of) + key terminology.
2. **Executive Overview — Performance & Retention Risk (As-Of)**  
   A one-page summary linking revenue performance to risk exposure and action capacity.
3. **Sales Performance — Revenue, Orders & AOV Drivers**  
   Revenue/Orders/AOV trends and drivers, Top-N countries and products.
4. **Customer Base & Segmentation — Segment Mix & Dynamics**  
   Snapshot-based segment membership, segment mix, and segment switch rate trend.
5. **Churn & Risk — Risk Load & Revenue Exposure (As-Of Snapshot)**  
   Scored customers, flagged population, risk mix, churn probability trend, revenue at risk, expected loss, geographic exposure.
6. **Action Playbook — Targeted Actions, Coverage & Priority (As-Of Snapshot)**  
   Capacity-based targeting (e.g., Top 15%), P1–P4 priorities, recommended actions/offers, and coverage metrics.
7. **Cohort & Retention — Acquisition Cohorts**  
   Cohort retention and cohort revenue from realized transactions (not snapshot estimates).
8. **Customer 360 — Selected Customer Profile & Risk (As-Of Snapshot)**  
   Single-customer view: value + risk + product-level order details at a snapshot.

---

## Data Science (Python) Layer
### Outputs used by the dashboard
The pipeline produces customer-level fields used throughout the report:
- `churn_probability` (predicted churn risk score)
- `risk_bucket` (Low / Medium / High)
- `churn_flag` (threshold-based **predicted risk indicator**, not observed churn)
- `expected_loss` (probability-weighted value loss proxy)
- capacity-based action targeting (e.g., Top15 via `action_flag_top15`) and action recommendation fields for the playbook (e.g., `priority`, `action`, `offer_type`, `message_angle`, `budget_suggestion`)

### Model summary (from `reports/churn_model_report.txt`)
- **Time-based cutoff (test starts):** 2011-06-30  
- **Selected model:** LightGBM  
- **ROC-AUC:** 0.8140  
- **PR-AUC:** 0.8582  
- **Features (13):**  
  `tenure_days`, `total_orders`, `total_revenue`, `avg_basket_value`, `avg_items_per_order`,  
  `avg_unique_skus`, `avg_days_between_orders`, `median_days_between_orders`, `recency_days`,  
  `revenue_last_30d`, `orders_last_30d`, `revenue_last_90d`, `orders_last_90d`

---

## BI / DAX Layer (Selected Highlights)
- Snapshot-aware KPIs (e.g., **At-Risk Customers**, **Revenue at Risk**, **Action Coverage %**)  
- Dynamic executive narrative (context-aware text summarizing selected Sales Period + Snapshot)
- Consistent numeric scaling (K/M) and formatting across KPIs
- Trends aligned to the correct timeline:
  - Sales trends by **InvoiceDate**
  - Risk trends across **SnapshotDate**

---

## Repository Structure (Recommended)
```text
.
├─ pbix/
│  └─ ChurnIntelligenceFinal.pbix
├─ src/
│  ├─ make_dataset.py
│  ├─ feature_engineering.py
│  ├─ churn_label.py
│  ├─ churn_model.py
│  ├─ segment_snapshot.py
│  ├─ campaign_actions.py
│  └─ run_pipeline.py
├─ data/                       # optional (prefer derived outputs for portfolio repos)
│  ├─ transactions_clean.csv
│  ├─ churn_scores.csv
│  ├─ customer_segment_snapshot.csv
│  └─ campaign_actions.csv
├─ reports/
│  ├─ churn_model_report.txt
│  ├─ REPORT.md
│  └─ REPORT_EN.md
└─ assets/
   ├─ 00-Start Here.png
   ├─ 01-Executive Overview.png
   ├─ 02-Sales Performance.png
   ├─ 03-Customer Base & Segmentation.png
   ├─ 04-Churn & Risk.png
   ├─ 05-Action Playbook.png
   ├─ 06-Cohort & Retention.png
   └─ 07-Customer 360.png
```

---

## Reproducibility (Optional)
If you want this repository to be executable end-to-end, add `requirements.txt` and run:

```bash
python src/run_pipeline.py
```

Then open the PBIX:
- `pbix/ChurnIntelligenceFinal.pbix`

---

## Notes
- `churn_flag` represents **predicted churn risk**, not observed churn events.
- Publish-to-web refresh behavior depends on Power BI Service data source configuration.

---

## Contact
- LinkedIn: `<YOUR_LINKEDIN>`
- Email: `<YOUR_EMAIL>`
