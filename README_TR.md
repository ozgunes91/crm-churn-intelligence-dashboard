# CRM Churn Intelligence Dashboard (Power BI + Python)

Transaction-level satış verisini müşteri seviyesine taşıyan; **satış performansı**, **churn risk zekâsı** ve **kapasite bazlı retention aksiyon planını** tek bir Power BI raporunda birleştiren portföy seviyesinde bir demo.

Bu proje **Online Retail II** veri seti üzerinde, **Veri Bilimi + BI** mantığıyla tasarlandı:
- **Python**: feature engineering, churn risk modelleme, skor üretimi, snapshot tabloları ve aksiyon listeleri
- **Power BI + DAX**: semantik modelleme, snapshot-aware KPI’lar, executive storytelling ve interaktif keşif

---

## 📌 Demo & Linkler
- **Interactive demo (Publish to web):** [Open the report](https://app.powerbi.com/view?r=eyJrIjoiYzc5NGUwZGEtMmM1ZS00NWIyLWJkZjEtMjc0ZDE0ZWI0YjM2IiwidCI6IjNiYjA1MzYzLTljMWYtNDM4My1iMzdkLWY2OWIxMWRkMzk5ZSIsImMiOjl9)

> Demo interaktiftir (sayfalar + slicer’lar). Refresh kapalı olsa bile rapor, son yayımlanan snapshot üzerinden demo olarak çalışır.”
---

## Görseller (Rapor Sayfaları)


| Sayfa | Önizleme |
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

## Bu raporu “gerçek hayat” yapan şey
### İki zaman ekseni: KPI karışması yok
Rapor, KPI’ların karışmaması için iki ayrı zaman bağlamını **bilerek** ayırır:

- **Sales Period (InvoiceDate)** → gerçekleşen satış KPI’ları (Revenue, Orders, AOV, trendler)
- **Snapshot (As-Of Date)** → risk/segment/expected loss/aksiyon karar noktası



---

## Sayfalar ve cevapladığı sorular
1. **Start Here**  
   Tanımlar ve kullanım: Sales Period vs Snapshot (As-Of) + terimler.
2. **Executive Overview — Performance & Retention Risk (As-Of)**  
   Performansı, risk maruziyetini ve aksiyon kapasitesini tek sayfada ilişkilendirir.
3. **Sales Performance — Revenue, Orders & AOV Drivers**  
   Revenue/Orders/AOV trendleri ve sürücüler; Top-N country/product.
4. **Customer Base & Segmentation — Segment Mix & Dynamics**  
   Snapshot bazlı segment üyeliği, segment mix ve segment switch rate trendi.
5. **Churn & Risk — Risk Load & Revenue Exposure (As-Of Snapshot)**  
   Scored/flagged müşteri yükü, risk dağılımı, churn probability trendi, revenue at risk, expected loss ve coğrafi maruziyet.
6. **Action Playbook — Targeted Actions, Coverage & Priority (As-Of Snapshot)**  
   Kapasite bazlı hedefleme (örn. Top15%), P1–P4 öncelikleri, önerilen aksiyon/teklifler ve coverage metrikleri.
7. **Cohort & Retention — Acquisition Cohorts**  
   İlk satın alma ayına göre cohort retention ve cohort revenue (yalnızca gerçekleşen satış).
8. **Customer 360 — Selected Customer Profile & Risk (As-Of Snapshot)**  
   Tek müşteri görünümü: değer + risk + ürün bazında sipariş detayları.

---

## Veri Bilimi (Python) katmanı
### Dashboard’da kullanılan çıktılar
Pipeline; raporda kullanılan müşteri seviyesinde şu alanları üretir:
- `churn_probability` (tahmin churn risk skoru)
- `risk_bucket` (Low / Medium / High)
- `churn_flag` (eşik bazlı **tahmini risk bayrağı**, observed churn değil)
- `expected_loss` (probability-weighted kayıp proxy’si)
- kapasite bazlı hedefleme (örn. `action_flag_top15`) ve playbook için aksiyon öneri alanları (`priority`, `action`, `offer_type`, `message_angle`, `budget_suggestion`)

### Model özeti (`reports/churn_model_report.txt`)
- Detay rapor: [churn_model_report.txt](reports/churn_model_report.txt)
- **Time-based cutoff (test başlangıcı):** 2011-06-30  
- **Seçilen model:** LightGBM  
- **ROC-AUC:** 0.8140  
- **PR-AUC:** 0.8582  
- **Feature’lar (13):**  
  `tenure_days`, `total_orders`, `total_revenue`, `avg_basket_value`, `avg_items_per_order`,  
  `avg_unique_skus`, `avg_days_between_orders`, `median_days_between_orders`, `recency_days`,  
  `revenue_last_30d`, `orders_last_30d`, `revenue_last_90d`, `orders_last_90d`

---

## Power BI / DAX katmanı (Öne çıkanlar)
- Snapshot-aware KPI’lar (**At-Risk Customers**, **Revenue at Risk**, **Action Coverage %** vb.)
- Sales Period + Snapshot bağlamını anlatan dinamik metin: **Executive Narrative**
- KPI’larda tutarlı sayı ölçekleme ve format (K/M)
- Trendler doğru eksende:
  - Sales trendleri **InvoiceDate**
  - Risk trendleri **SnapshotDate**

---

## Çalıştırılabilirlik (Opsiyonel)

### Dataset (Online Retail II)

Bu repo ham veriyi boyut nedeniyle içermez.

1) Online Retail II veri setini **Kaggle** veya resmi kaynaktan indirin.  
2) Dosyayı şu klasöre koyun: `data/raw/`  
3) Ardından `src/` altındaki scriptleri çalıştırın.

> Not: Veri dosya adı/kapsamı kaynağa göre değişebilir. Scriptlerdeki `DATA_PATH` / argümanları indirilen dosya adına göre güncelleyin.

```bash
pip install -r requirements.txt
python src/run_pipeline.py
```
---

## Notlar
- `churn_flag` **tahmini churn riskini** temsil eder; observed churn olayı değildir.
- Publish-to-web refresh davranışı Power BI Service data source konfigürasyonuna bağlıdır.

---

## İletişim
- E-posta: `ozgekayagunes@gmail.com`
