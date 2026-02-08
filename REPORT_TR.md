# Proje Raporu — CRM Churn Intelligence Dashboard (Power BI + Python)

## 1) Amaç
Bu proje, transaction-level satış verisini müşteri seviyesine taşıyarak:
- **Satış performansını** (Revenue / Orders / AOV) izlemek,
- **Churn risk maruziyetini** (risk dağılımı, Revenue at Risk, Expected Loss) görünür kılmak,
- **Kapasite kısıtı altında** (örn. Top15%) aksiyon önceliklendirme ile operasyonel retention hedef listesi üretmek
amacıyla geliştirilmiştir.

## 2) KPI doğruluğu için iki zaman ekseni
Rapor iki ayrı zaman bağlamı ile çalışır:
- **Sales Period (InvoiceDate):** gerçekleşen satış KPI’ları ve satış trendleri
- **Snapshot (As-Of Date):** risk/segment/expected loss ve aksiyon karar noktası

Bu ayrım, satış dönemindeki KPI’larla “as-of risk” metriklerinin aynı filtrede yanlış yorumlanmasını engeller.

## 3) Veri Bilimi (Python) katmanı
Python pipeline’ın ana çıktıları:
- müşteri seviyesinde feature engineering (RFM/tenure/recency + rolling window metrikleri)
- time-based split ile churn risk modelleme ve skor üretimi
- dashboard’da kullanılan kolonlar:
  - `churn_probability`, `risk_bucket`, `churn_flag`
  - `expected_loss` (probability-weighted kayıp proxy’si)
  - kapasite bazlı hedefleme (örn. `action_flag_top15`) ve aksiyon önerileri (Action Playbook: `priority`, `action`, `offer_type`, `message_angle`, `budget_suggestion`)

### Model metrik özeti (`churn_model_report.txt`)
- Cutoff (test başlangıcı): **2011-06-30**
- Seçilen model: **LightGBM**
- ROC-AUC: **0.8140**
- PR-AUC: **0.8582**
- Feature sayısı: **13**

> Not: `churn_flag` gerçek “observed churn” değil, **tahmin skoruna dayalı eşik bayrağıdır**.

## 4) Power BI / DAX katmanı
- Snapshot-aware ölçüler: At-Risk Customers, Revenue at Risk, Action Coverage vb.
- Context-aware Executive Narrative (Sales Period + Snapshot seçimine göre otomatik anlatı)
- Dinamik sayı formatlama (K/M) ve KPI standardizasyonu
- Trendler doğru eksende:
  - Sales trendleri **InvoiceDate**
  - Risk trendleri **SnapshotDate**

## 5) Sayfalar ve kullanım
- **Executive Overview:** performans + risk + aksiyon kapasitesi tek bakış
- **Churn & Risk:** risk yükü, churn prob trendi, revenue exposure, geo dağılım
- **Action Playbook:** Top15 hedefleme, P1–P4, önerilen aksiyonlar
- **Customer 360:** tek müşteri değer + risk + ürün/işlem detayı
- **Cohort & Retention:** acquisition cohort retention & gelir (yalnızca gerçekleşen satış)
- **Sales Performance / Segmentation:** büyüme sürücüleri, segment mix ve değişimi

## 6) Portföy notu
Publish-to-web demo interaktiftir (slicer’lar çalışır). Refresh davranışı Power BI Service data source ayarlarına bağlıdır.
