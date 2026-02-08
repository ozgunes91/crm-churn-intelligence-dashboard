# Project Report — CRM Churn Intelligence Dashboard (Power BI + Python)

## 1) Goal
This project transforms transaction-level sales data into customer-level intelligence to:
- monitor **sales performance** (Revenue / Orders / AOV),
- quantify **churn risk exposure** (risk mix, Revenue at Risk, Expected Loss),
- and generate an operational retention target list under **capacity constraints** (e.g., Top15%).

## 2) Two timelines for KPI integrity
The report intentionally separates two time contexts:
- **Sales Period (InvoiceDate):** realized sales KPIs and sales trends
- **Snapshot (As-Of Date):** the decision point for risk/segments/expected loss/actions

This prevents “context mixing” and keeps definitions consistent.

## 3) Data Science (Python) layer
Main outputs:
- customer-level feature engineering (RFM/tenure/recency + rolling windows)
- time-based split churn modeling and scoring
- fields used in the dashboard:
  - `churn_probability`, `risk_bucket`, `churn_flag`
  - `expected_loss` (probability-weighted value loss proxy)
  - capacity-based targeting (e.g., `action_flag_top15`) and action recommendations (Action Playbook: `priority`, `action`, `offer_type`, `message_angle`, `budget_suggestion`)

### Model summary (`churn_model_report.txt`)
- Cutoff (test starts): **2011-06-30**
- Selected model: **LightGBM**
- ROC-AUC: **0.8140**
- PR-AUC: **0.8582**
- Number of features: **13**

> Note: `churn_flag` is a threshold-based **predicted risk indicator**, not observed churn.

## 4) Power BI / DAX layer
- Snapshot-aware measures: At-Risk Customers, Revenue at Risk, Action Coverage, etc.
- Context-aware Executive Narrative (auto-generated summary based on Sales Period + Snapshot)
- Dynamic numeric scaling (K/M) and KPI standardization
- Trends aligned to the correct timeline:
  - Sales trends by **InvoiceDate**
  - Risk trends across **SnapshotDate**

## 5) Pages
- **Executive Overview:** performance + risk + action capacity in one place
- **Churn & Risk:** risk load, churn probability trend, exposure, geo distribution
- **Action Playbook:** Top15 targeting, P1–P4 priorities, recommended actions
- **Customer 360:** single customer value + risk + product/order details
- **Cohort & Retention:** acquisition cohorts retention and revenue (realized sales only)
- **Sales Performance / Segmentation:** growth drivers, segment mix and dynamics

## 6) Portfolio note
The publish-to-web demo is interactive (slicers work). Refresh behavior depends on Power BI Service data source configuration.
