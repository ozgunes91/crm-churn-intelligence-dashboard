# MEASURES_CORE (DAX Export)

> Generated from the current PBIX model via Tabular Editor.
> Output location: Desktop


## 00 Base

### Latest Date (All)

```DAX
CALCULATE(MAX(DimDate[Date]), ALL(DimDate))
```

### Previous Snapshot Date

```DAX

VAR d = [Selected Snapshot Date]
RETURN
CALCULATE(
    MAX(DimSnapshotDate[SnapshotDate]),
    FILTER(ALL(DimSnapshotDate[SnapshotDate]), DimSnapshotDate[SnapshotDate] < d)
)
```

### Sales Period

```DAX
VAR d1 = MIN ( DimDate[Date] )
VAR d2 = MAX ( DimDate[Date] )
RETURN
IF (
    ISBLANK ( d1 ) || ISBLANK ( d2 ),
    BLANK(),
    FORMAT ( d1, "dd MMM yyyy" ) & " – " & FORMAT ( d2, "dd MMM yyyy" )
)
```

### Selected Date

```DAX
COALESCE(SELECTEDVALUE(DimDate[Date]), [Latest Date (All)])
```

### Selected Snapshot Date

```DAX

COALESCE(
    SELECTEDVALUE(DimSnapshotDate[SnapshotDate]),
    MAX(DimSnapshotDate[SnapshotDate])
)
```

### Snapshot Date

```DAX

FORMAT([Selected Snapshot Date], "dd mmm yyyy")
```


## 00 Core/Dates & Snapshot

### Selected Action Mode

```DAX

SELECTEDVALUE(DimActionMode[ActionMode], "All Actions")
```

### Selected Priority Customers (As Of)

```DAX

VAR d   = [Selected Snapshot Date]
VAR e = [Is Top15 Mode]
RETURN
CALCULATE(
    DISTINCTCOUNT(FactCustomerActions[CustomerID]),
    TREATAS({d}, FactCustomerActions[SnapshotDate]),
    IF(
        e = 1,
        FactCustomerActions[action_flag_top15] = 1,
        NOT ISBLANK(FactCustomerActions[action])
    )
)
```

### Selected Priority Customers (Trend)

```DAX

VAR e = [Is Top15 Mode]
RETURN
CALCULATE(
    DISTINCTCOUNT(FactCustomerActions[CustomerID]),
    IF(
        e = 1,
        FactCustomerActions[action_flag_top15] = 1,
        NOT ISBLANK(FactCustomerActions[action])
    )
)
```

### Selected Sales Period (Text)

```DAX

VAR ym =
    SELECTEDVALUE ( DimDate[YearMonthText] )
RETURN
IF ( ISBLANK ( ym ), "multiple periods", ym )
```

### Selected Snapshot (Text)

```DAX

VAR ym =
    SELECTEDVALUE ( DimSnapshotDate[SnapshotYearMonthText])
RETURN
IF ( ISBLANK ( ym ), "latest snapshot", ym )
```


## 00 Core/UI & Text

### Executive Narrative

```DAX

VAR SalesPeriod    = [Selected Sales Period (Text)]
VAR SnapshotPeriod = [Selected Snapshot (Text)]

/* ---- Helpers: Dynamic currency formatting (K/M/B) ---- */
VAR _Revenue = [Revenue]
VAR RevenueValue =
    SWITCH(
        TRUE(),
        ISBLANK(_Revenue), BLANK(),
        ABS(_Revenue) >= 1000000000, "$" & FORMAT(_Revenue / 1000000000, "#,##0.00") & "B",
        ABS(_Revenue) >= 1000000,    "$" & FORMAT(_Revenue / 1000000,    "#,##0.00") & "M",
        ABS(_Revenue) >= 1000,       "$" & FORMAT(_Revenue / 1000,       "#,##0.0")  & "K",
                                  "$" & FORMAT(_Revenue,                "#,##0")
    )

VAR _RiskRevenue = [Revenue at Risk (High+Med, As Of)]
VAR RiskRevenueValue =
    SWITCH(
        TRUE(),
        ISBLANK(_RiskRevenue), BLANK(),
        ABS(_RiskRevenue) >= 1000000000, "$" & FORMAT(_RiskRevenue / 1000000000, "#,##0.00") & "B",
        ABS(_RiskRevenue) >= 1000000,    "$" & FORMAT(_RiskRevenue / 1000000,    "#,##0.00") & "M",
        ABS(_RiskRevenue) >= 1000,       "$" & FORMAT(_RiskRevenue / 1000,       "#,##0.0")  & "K",
                                      "$" & FORMAT(_RiskRevenue,                "#,##0")
    )

/* ---- Other KPIs ---- */
VAR OrdersValue =
    IF( ISBLANK([Orders]), BLANK(), FORMAT([Orders], "#,##0") )

VAR RiskCustomersValue =
    IF( ISBLANK([At-Risk Customers (High+Med, As Of)]), BLANK(),
        FORMAT([At-Risk Customers (High+Med, As Of)], "#,##0")
    )

VAR ActionCoverageValue =
    IF( ISBLANK([Action Coverage % (As Of, of High+Med)]), BLANK(),
        FORMAT([Action Coverage % (As Of, of High+Med)], "0.0%")
    )

/* ---- Final text ---- */
RETURN
"In the selected sales period (" & SalesPeriod & "), revenue reached "
& RevenueValue & " with stable order volume (" & OrdersValue & " orders). "
& "As of the " & SnapshotPeriod & " snapshot, "
& RiskCustomersValue & " customers are classified as Medium or High risk, "
& "representing " & RiskRevenueValue & " in customer value at risk. "
& "Current action capacity addresses only " & ActionCoverageValue
& " of at-risk customers, highlighting a prioritization gap between churn exposure and retention execution."


```


## 01 Sales - Base

### AOV

```DAX
DIVIDE([Revenue],[Orders])
```

### ARPU

```DAX
DIVIDE([Revenue],[Customers])
```

### Customers

```DAX
DISTINCTCOUNT(FactSales[CustomerID])
```

### New Customers (Selected Period)

```DAX

VAR EndDate = [Selected Date]
VAR StartDate = EDATE(EndDate, -12) + 1
RETURN
CALCULATE(
    DISTINCTCOUNT(DimCustomer[CustomerID]),
    DimCustomer[FirstPurchaseDate] >= StartDate,
    DimCustomer[FirstPurchaseDate] <= EndDate
)
```

### Orders

```DAX
DISTINCTCOUNT(FactSales[InvoiceNo])
```

### Revenue

```DAX
SUM(FactSales[TotalPrice])
```


## 02 Sales - Time

### Is Completed Month

```DAX
VAR maxD = MAX(DimDate[Date])
RETURN IF( maxD = EOMONTH(maxD, 0), 1, 0 )
```

### Orders LY

```DAX

CALCULATE(
    [Orders],
    DATEADD('DimDate'[Date], -1, YEAR)
)
```

### Orders MoM %

```DAX

VAR curr = [Orders]
VAR prev = [Orders PM]
RETURN
IF(
    ISBLANK(prev) || prev = 0,
    BLANK(),
    DIVIDE(curr - prev, prev)
)
```

### Orders MoM % (Complete Month)

```DAX

IF([Is Completed Month] = 1, [Orders MoM %], BLANK())
```

### Orders PM

```DAX

CALCULATE(
    [Orders],
    DATEADD('DimDate'[Date], -1, MONTH)
)
```

### Orders YoY %

```DAX

VAR curr = [Orders]
VAR prev = [Orders LY]
RETURN
IF(
    ISBLANK(prev) || prev = 0,
    BLANK(),
    DIVIDE(curr - prev, prev)
)
```

### Orders YoY % (Complete Month)

```DAX

IF([Is Completed Month] = 1, [Orders YoY %], BLANK())
```

### Revenue LY

```DAX

CALCULATE(
    [Revenue],
    DATEADD('DimDate'[Date], -1, YEAR)
)
```

### Revenue MoM %

```DAX

VAR curr = [Revenue]
VAR prev = [Revenue PM]
RETURN
IF(
    ISBLANK(prev) || prev = 0,
    BLANK(),
    DIVIDE(curr - prev, prev)
)
```

### Revenue MoM % (Complete Month)

```DAX

IF([Is Completed Month] = 1, [Revenue MoM %], BLANK())
```

### Revenue PM

```DAX

CALCULATE(
    [Revenue],
    DATEADD('DimDate'[Date], -1, MONTH)
)
```

### Revenue YoY %

```DAX

VAR curr = [Revenue]
VAR prev = [Revenue LY]
RETURN
IF(
    ISBLANK(prev) || prev = 0,
    BLANK(),
    DIVIDE(curr - prev, prev)
)
```

### Revenue YoY % (Complete Month)

```DAX

IF([Is Completed Month] = 1, [Revenue YoY %], BLANK())
```


## 03 TopN

### Is Top15 Mode

```DAX

IF([Selected Action Mode] = "Top15%", 1, 0)
```

### Revenue Rank - Country

```DAX
RANKX (
    ALLSELECTED ( DimSalesCountry[Country] ),
    [Revenue],
    ,
    DESC,
    DENSE
)
```

### Revenue Rank - StockCode

```DAX
RANKX (
    ALLSELECTED ( DimProduct[StockCode] ),
    [Revenue],
    ,
    DESC,
    DENSE
)
```

### Selected TopN

```DAX

SELECTEDVALUE ( 'TopN Parameter'[N], 10 )
```

### Show TopN Country

```DAX

VAR r = [Revenue Rank - Country]
VAR n = [Selected TopN]
RETURN
IF ( NOT ISBLANK ( [Revenue] ) && r <= n, 1, 0 )

```

### Show TopN StockCode

```DAX

VAR r = [Revenue Rank - StockCode]
VAR n = [Selected TopN]
RETURN
IF ( NOT ISBLANK ( [Revenue] ) && r <= n, 1, 0 )

```


## 04 Churn - Impact

### Expected Loss (High+Med, As Of)

```DAX

CALCULATE(
    [Expected Revenue Loss (As Of)],
    FactChurnScores[risk_bucket] IN {"High","Medium"}
)
```

### Expected Revenue Loss (As Of)

```DAX

SUM(FactChurnScores[expected_loss])
```

### Revenue at Risk (High+Med, As Of)

```DAX

CALCULATE(
    [Revenue (As Of)],
    FactChurnScores[risk_bucket] IN {"High","Medium"}
)
```


## 04 Churn - Movement

### Revenue at Risk (High+Med, Prev)

```DAX

VAR dPrev = [Previous Snapshot Date]
RETURN
CALCULATE(
    [Revenue at Risk (High+Med, As Of)],
    TREATAS({dPrev}, DimSnapshotDate[SnapshotDate])
)
```

### Revenue at Risk Δ (vs Previous Snapshot)

```DAX

[Revenue at Risk (High+Med, As Of)] - [Revenue at Risk (High+Med, Prev)]
```

### Segment Switch Rate (Vs Prev)

```DAX
VAR dCur = [Selected Snapshot Date]
VAR dPrev = [Previous Snapshot Date]
VAR kCur = INT(dCur)
VAR kPrev = INT(dPrev)
RETURN
IF(
    ISBLANK(dPrev),
    BLANK(),
    VAR Cur =
        SELECTCOLUMNS(
            FILTER(ALL(FactChurnScores), INT(FactChurnScores[SnapshotDate]) = kCur),
            "CustomerID", FactChurnScores[CustomerID],
            "Seg", FactChurnScores[segment]
        )
    VAR Prev =
        SELECTCOLUMNS(
            FILTER(ALL(FactChurnScores), INT(FactChurnScores[SnapshotDate]) = kPrev),
            "CustomerID", FactChurnScores[CustomerID],
            "SegPrev", FactChurnScores[segment]
        )
    VAR Joined = NATURALLEFTOUTERJOIN(Cur, Prev)
    VAR Comparable = FILTER(Joined, NOT ISBLANK([SegPrev]))
    VAR Switched = COUNTROWS(FILTER(Comparable, [Seg] <> [SegPrev]))
    VAR Base = COUNTROWS(Comparable)
    RETURN DIVIDE(Switched, Base, 0)
)
```


## 04 Churn - Risk

### Churn Flag Rate (As Of)

```DAX
DIVIDE([Churn Flagged Customers (As Of)], [Scored Customers (As Of)])
```

### Churn Flagged Customers (As Of)

```DAX

CALCULATE(
    DISTINCTCOUNT(FactChurnScores[CustomerID]),
    FactChurnScores[churn_flag] = 1
)
```

### Country Risk Mix (As Of)

```DAX

VAR hi = CALCULATE( DISTINCTCOUNT(FactChurnScores[CustomerID]), FactChurnScores[risk_bucket] = "High" )
VAR md = CALCULATE( DISTINCTCOUNT(FactChurnScores[CustomerID]), FactChurnScores[risk_bucket] = "Medium" )
VAR lo = CALCULATE( DISTINCTCOUNT(FactChurnScores[CustomerID]), FactChurnScores[risk_bucket] = "Low" )
RETURN
"High: " & FORMAT(hi, "#,0") & " | Med: " & FORMAT(md, "#,0") & " | Low: " & FORMAT(lo, "#,0")

```

### Median Churn Probability (As Of)

```DAX

MEDIAN(FactChurnScores[churn_probability])
```

### Scored Customers (As Of)

```DAX

DISTINCTCOUNT(FactChurnScores[CustomerID])
```


## 04 Churn - Trend

### Avg Churn Probability (Trend)

```DAX
AVERAGE(FactChurnScores[churn_probability])
```

### Revenue at Risk (High+Med, Trend)

```DAX
CALCULATE(SUM(FactChurnScores[total_revenue]), FactChurnScores[risk_bucket] IN {"High","Medium"})
```


## 05 Segment - Base

### Avg Recency Days (As Of)

```DAX
VAR d = [Selected Snapshot Date]
RETURN CALCULATE(AVERAGE(FactChurnScores[recency_days]), TREATAS({d}, FactChurnScores[SnapshotDate]))
```

### Customers (As Of)

```DAX
[Scored Customers (As Of)]
```

### Revenue (As Of)

```DAX

SUM(FactChurnScores[total_revenue])
```


## 05 Segment - Trend

### Customers (Trend)

```DAX
DISTINCTCOUNT(FactChurnScores[CustomerID])
```


## 06 Actions - Base

### Action Coverage %

```DAX

DIVIDE(
    [Action Customers (As Of)],
    [Scored Customers (As Of)],
    0
)
```

### Action Coverage % (As Of, of High+Med)

```DAX

DIVIDE(
    [Action List Customers (High+Med, As Of)],
    [At-Risk Customers (High+Med, As Of)],
    0
)
```

### Action Customers (As Of)

```DAX

VAR d   = [Selected Snapshot Date]
VAR e  = [Is Top15 Mode]
RETURN
CALCULATE(
    DISTINCTCOUNT(FactCustomerActions[CustomerID]),
    TREATAS({d}, FactCustomerActions[SnapshotDate]),
    IF(
        e = 1,
        FactCustomerActions[action_flag_top15] = 1,
        NOT ISBLANK(FactCustomerActions[action])
    ),
    REMOVEFILTERS(DimPriority)
)

```

### Action List Customers (As Of)

```DAX

VAR d = [Selected Snapshot Date]
VAR mode = [Selected Action Mode]
RETURN
COALESCE(
    CALCULATE(
        DISTINCTCOUNT(FactCustomerActions[CustomerID]),
        TREATAS({d}, FactCustomerActions[SnapshotDate]),
        REMOVEFILTERS(DimPriority[priority]),
        SWITCH(
            mode,
            "Top15", FactCustomerActions[action_flag_top15] = 1,
            "AllActions", TRUE(),
            FactCustomerActions[action_flag_top15] = 1
        )
    ),
    0
)

```

### Action List Customers (High+Med, As Of)

```DAX

VAR d = [Selected Snapshot Date]
VAR RiskCustomers =
    CALCULATETABLE(
        VALUES(FactChurnScores[CustomerID]),
        TREATAS({d}, FactChurnScores[SnapshotDate]),
        FactChurnScores[risk_bucket] IN {"High","Medium"}
    )
RETURN
CALCULATE(
    DISTINCTCOUNT(FactCustomerActions[CustomerID]),
    TREATAS({d}, FactCustomerActions[SnapshotDate]),
    TREATAS(RiskCustomers, FactCustomerActions[CustomerID]),
    FactCustomerActions[action_flag_top15] = 1   -- 🔥 esas filtre bu
)
```

### At-Risk Customers (High+Med, As Of)

```DAX

CALCULATE(
    DISTINCTCOUNT(FactChurnScores[CustomerID]),
    FactChurnScores[risk_bucket] IN {"High","Medium"}
)
```

### In Action List (Row)

```DAX

VAR e = [Is Top15 Mode]
VAR hasAction =
    IF(
        e = 1,
        MAX(FactCustomerActions[action_flag_top15]) = 1,
        NOT ISBLANK(MAX(FactCustomerActions[action]))
    )
RETURN
IF(hasAction, 1, 0)
```


## 06 Actions - Priority

### Priority Share (As Of)

```DAX

DIVIDE(
    [Selected Priority Customers (As Of)],
    [Action Customers (As Of)],
    0
)
```


## 06 Actions - Trend

### Action Customers (Trend)

```DAX

VAR e = [Is Top15 Mode]
RETURN
CALCULATE(
    DISTINCTCOUNT(FactCustomerActions[CustomerID]),
    IF(
        e = 1,
        FactCustomerActions[action_flag_top15] = 1,
        NOT ISBLANK(FactCustomerActions[action])
    ),
    REMOVEFILTERS(DimPriority)
)
```


## 07 Cohort & Retention

### Active Customers (Cohort x Month)

```DAX
[Customers]
```

### Cohort Revenue (Cohort x Month)

```DAX
[Revenue]
```

### Cohort Size (Customers)

```DAX
CALCULATE(DISTINCTCOUNT(DimCustomer[CustomerID]), ALLEXCEPT(DimCustomer, DimCustomer[CohortMonthStart]))
```

### Repeat Rate (Last 90D)

```DAX
VAR AnchorDate = [Selected Date]
VAR WindowDates =
    DATESINPERIOD ( DimDate[Date], AnchorDate, -90, DAY )
VAR CustOrders =
    SUMMARIZECOLUMNS (
        FactSales[CustomerID],
        WindowDates,
        "OrderCnt", DISTINCTCOUNT ( FactSales[InvoiceNo] )
    )
VAR RepeatCust =
    COUNTROWS ( FILTER ( CustOrders, [OrderCnt] >= 2 ) )
VAR ActiveCust =
    COUNTROWS ( FILTER ( CustOrders, [OrderCnt] >= 1 ) )
RETURN
    DIVIDE ( RepeatCust, ActiveCust )
```

### Retention % (Cohort Heatmap)

```DAX
VAR cohortSize = [Cohort Size (Customers)]
RETURN DIVIDE([Active Customers (Cohort x Month)], cohortSize)
```


## 08 Customer 360/Detail

### Customer Churn Flag (As Of)

```DAX

VAR c = [Selected Customer ID]
VAR d = [Selected Snapshot Date]
RETURN
IF(
    ISBLANK(c) || ISBLANK(d),
    BLANK(),
    CALCULATE(
        MAX(FactChurnScores[churn_flag]),
        TREATAS({c}, FactChurnScores[CustomerID]),
        TREATAS({d}, FactChurnScores[SnapshotDate])
    )
)
```

### Customer Churn Probability (As Of)

```DAX

VAR cid = [Selected Customer ID]
VAR snap = [Effective Snapshot Date]
RETURN
IF(
    NOT ISBLANK(cid) && NOT ISBLANK(snap),
    CALCULATE(
        MAX(FactChurnScores[churn_probability]),
        TREATAS( { cid }, FactChurnScores[CustomerID] ),
        TREATAS( { snap }, FactChurnScores[SnapshotDate] )
    )
)
```

### Customer Expected Loss (As Of)

```DAX

VAR cid      = [Selected Customer ID]
VAR snapDate = DATEVALUE([Effective Snapshot Date])
RETURN
IF(
    ISBLANK(cid) || ISBLANK(snapDate),
    BLANK(),
    CALCULATE(
        SELECTEDVALUE(FactChurnScores[expected_loss]),
        TREATAS({cid},      FactChurnScores[CustomerID]),
        TREATAS({snapDate}, FactChurnScores[SnapshotDate])
    )
)

```

### Customer First Purchase Date

```DAX
VAR cid = [Selected Customer ID]
RETURN
IF(
    ISBLANK(cid),
    BLANK(),
    CALCULATE(
        MIN(FactSales[InvoiceDate_Date]),
        REMOVEFILTERS(DimDate),
        TREATAS({cid}, FactSales[CustomerID])
    )
)
```

### Customer Has History As Of

```DAX
VAR firstD = [Customer First Purchase Date]
VAR snap  = [Effective Snapshot Date]
RETURN
IF(
    NOT ISBLANK(firstD) && NOT ISBLANK(snap) && firstD <= snap,
    1,
    0
)
```

### Customer Last Purchase Date (As Of)

```DAX
VAR cid = [Selected Customer ID]
VAR snap = [Effective Snapshot Date]
RETURN
IF(
    ISBLANK(cid) || ISBLANK(snap),
    BLANK(),
    CALCULATE(
        MAX(FactSales[InvoiceDate_Date]),
        REMOVEFILTERS(DimDate),
        TREATAS({cid}, FactSales[CustomerID]),
        FactSales[InvoiceDate_Date] <= snap
    )
)
```

### Customer Orders (As Of)

```DAX
VAR cid = [Selected Customer ID]
VAR snap = [Effective Snapshot Date]
RETURN
IF(
    ISBLANK(cid) || ISBLANK(snap),
    BLANK(),
    CALCULATE(
        [Orders],
        REMOVEFILTERS(DimDate),
        TREATAS({cid}, FactSales[CustomerID]),
        FactSales[InvoiceDate_Date] <= snap
    )
)
```

### Customer Revenue (As Of)

```DAX
VAR cid = [Selected Customer ID]
VAR snap = [Effective Snapshot Date]
RETURN
IF(
    ISBLANK(cid) || ISBLANK(snap),
    BLANK(),
    CALCULATE(
        [Revenue],
        REMOVEFILTERS(DimDate),
        TREATAS({cid}, FactSales[CustomerID]),
        FactSales[InvoiceDate_Date] <= snap
    )
)
```

### Effective Snapshot Date

```DAX

VAR cid = [Selected Customer ID]
VAR snapSel = [Selected Snapshot Date]
VAR snapAvail =
    CALCULATE(
        MAX ( FactChurnScores[SnapshotDate] ),
        TREATAS( { cid }, FactChurnScores[CustomerID] ),
        FactChurnScores[SnapshotDate] <= snapSel
    )
RETURN
COALESCE( snapAvail, snapSel )
```

### Has Churn Score (As Of)

```DAX
VAR cid = [Selected Customer ID]
VAR snap = [Effective Snapshot Date]
VAR cnt =
    IF(
        ISBLANK(cid) || ISBLANK(snap),
        BLANK(),
        CALCULATE(
            COUNTROWS(FactChurnScores),
            TREATAS({cid}, FactChurnScores[CustomerID]),
            TREATAS({snap}, FactChurnScores[SnapshotDate])
        )
    )
RETURN IF( NOT ISBLANK(cnt) && cnt > 0, 1, 0 )
```

### Selected Customer ID

```DAX

SELECTEDVALUE(DimCustomer[CustomerID])
```


## 08 Customer 360/KPI

### Customer 360 Status

```DAX
VAR cid = [Selected Customer ID]
VAR snapSel = [Selected Snapshot Date]
VAR snapEff = [Effective Snapshot Date]
VAR hasHist = [Customer Has History As Of]
VAR hasScore = [Has Churn Score (As Of)]
RETURN
SWITCH(
    TRUE(),
    ISBLANK(cid), "Select a CustomerID.",
    ISBLANK(snapSel), "Select a Snapshot Date.",
    hasHist = 0, "Customer not active yet at this snapshot (no purchases on/before effective date).",
    hasScore = 0, "No churn score available for this customer at the effective snapshot date.",
    snapEff <> snapSel, "No record for selected date → showing nearest available snapshot.",
    "✅ OK — Data available at snapshot"
)
```

### Customer 360 Summary

```DAX
VAR cust = [Selected Customer ID]
VAR snapSel = [Selected Snapshot Date]
VAR snapEff = [Effective Snapshot Date]
VAR hasHist = [Customer Has History As Of]
VAR seg  = SELECTEDVALUE( FactChurnScores[segment], "N/A" )
VAR risk = SELECTEDVALUE( FactChurnScores[risk_bucket], "N/A" )
VAR p    = [Customer Churn Probability (As Of)]
VAR loss = [Customer Expected Loss (As Of)]
VAR lpd  = [Customer Last Purchase Date (As Of)]
RETURN
IF(
    ISBLANK(cust) || ISBLANK(snapSel),
    "Select a Snapshot Date and CustomerID to view the customer story.",
    IF(
        hasHist = 0,
        "Customer " & cust & " has no purchases on/before the effective snapshot date (" & FORMAT(snapEff, "dd/MM/yyyy") & ").",
        "Customer " & cust &
        " | Snapshot: " & FORMAT(snapEff, "dd/MM/yyyy") &
        " | Segment: " & seg &
        " | Risk: " & risk &
        " | Churn Prob: " & FORMAT(p, "0.0%") &
        " | Exp. Loss: " & FORMAT(loss, "$#,0") &
        " | Last Purchase: " & FORMAT(lpd, "dd MMM yyyy")
    )
)
```

### Customer AOV (As Of)

```DAX

VAR rev = [Customer Revenue (As Of)]
VAR ord = [Customer Orders (As Of)]
RETURN
IF( NOT ISBLANK(ord) && ord > 0, DIVIDE(rev, ord) )
```

### Customer Churn Status Label (As Of)

```DAX

VAR f = [Customer Churn Flag (As Of)]
RETURN
SWITCH(
    TRUE(),
    ISBLANK(f), "N/A",
    f = 1, "Churn Flagged",
    "Not Flagged"
)
```

### Customer Revenue Trend (Monthly, As Of)

```DAX

VAR cid  = [Selected Customer ID]
VAR snap = [Effective Snapshot Date]
VAR axisMax = MAX(DimDate[Date])
RETURN
IF(
    ISBLANK(cid) || ISBLANK(snap) || axisMax > snap,
    BLANK(),
    CALCULATE(
        [Revenue],
        REMOVEFILTERS(DimDate),               -- slicer’ı kır
        KEEPFILTERS(VALUES(DimDate[Date])),   -- eksen bağlamını KORU (kritik)
        TREATAS({cid}, FactSales[CustomerID])
    )
)
```

### Customer Units (As Of)

```DAX
VAR cid = [Selected Customer ID]
VAR snap = [Effective Snapshot Date]
RETURN
IF(
    ISBLANK(cid) || ISBLANK(snap),
    BLANK(),
    CALCULATE(
        SUM(FactSales[Quantity]),
        REMOVEFILTERS(DimDate),
        TREATAS({cid}, FactSales[CustomerID]),
        FactSales[InvoiceDate_Date] <= snap
    )
)
```

### Product Last Purchase Date (As Of)

```DAX

VAR snap = [Effective Snapshot Date]
RETURN
IF(
    ISBLANK(snap),
    BLANK(),
    CALCULATE(
        MAX(FactSales[InvoiceDate]),
        FILTER(ALL(DimDate[Date]), DimDate[Date] <= snap)
    )
)
```

### Product Qty (As Of)

```DAX

VAR snap = [Effective Snapshot Date]
RETURN
CALCULATE(
    SUM(FactSales[Quantity]),
    FILTER(ALL(DimDate[Date]), DimDate[Date] <= snap)
)
```

### Product Revenue (As Of)

```DAX

VAR snap = [Effective Snapshot Date]
RETURN
CALCULATE(
    [Revenue],
    FILTER(ALL(DimDate[Date]), DimDate[Date] <= snap)
)
```


## 99_Unused (Hidden)

### Tooltip - Product Description

```DAX

SELECTEDVALUE( DimProduct[Description] )
```

