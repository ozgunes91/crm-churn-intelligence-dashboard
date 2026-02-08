from pathlib import Path
import pandas as pd


def ensure_dir(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)


def main():
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    RAW = PROJECT_ROOT / "data" / "raw" / "online_retail_II.csv"
    OUT = PROJECT_ROOT / "data" / "processed" / "transactions_clean.csv"

    df = pd.read_csv(RAW, encoding_errors="ignore")

    original_cols = df.columns.tolist()

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
    )

    rename_map = {
        "invoice": "InvoiceNo",
        "invoiceno": "InvoiceNo",
        "invoice_no": "InvoiceNo",

        "customer_id": "CustomerID",
        "customerid": "CustomerID",
        "customer_id_": "CustomerID",

        "price": "UnitPrice",
        "unitprice": "UnitPrice",
        "unit_price": "UnitPrice",

        "invoicedate": "InvoiceDate",
        "invoice_date": "InvoiceDate",

        "stockcode": "StockCode",
        "stock_code": "StockCode",
    }

    df = df.rename(columns={c: rename_map.get(c, c) for c in df.columns})

    canonical = {
        "invoiceno": "InvoiceNo",
        "stockcode": "StockCode",
        "description": "Description",
        "quantity": "Quantity",
        "invoicedate": "InvoiceDate",
        "unitprice": "UnitPrice",
        "customerid": "CustomerID",
        "country": "Country",
        "totalprice": "TotalPrice",
    }
    df = df.rename(columns={c: canonical.get(c.lower(), c) for c in df.columns})

    required_cols = ["InvoiceDate", "CustomerID", "InvoiceNo", "Quantity", "UnitPrice"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(
            f"❌ Missing required columns: {missing}\n"
            f"Raw columns were: {original_cols}\n"
            f"Normalized columns are: {df.columns.tolist()}"
        )

    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    df = df.dropna(subset=["InvoiceDate", "CustomerID", "InvoiceNo"])

    df["CustomerID"] = (
        df["CustomerID"].astype(str).str.replace(".0", "", regex=False).str.strip()
    )

    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
    df["UnitPrice"] = pd.to_numeric(df["UnitPrice"], errors="coerce")
    df = df.dropna(subset=["Quantity", "UnitPrice"])
    df = df[(df["Quantity"] > 0) & (df["UnitPrice"] > 0)]

    df["TotalPrice"] = df["Quantity"] * df["UnitPrice"]

    keep = [
        "InvoiceDate", "InvoiceNo", "CustomerID",
        "StockCode", "Description", "Quantity", "UnitPrice", "TotalPrice", "Country"
    ]
    keep = [c for c in keep if c in df.columns]
    df = df[keep].sort_values("InvoiceDate")

    ensure_dir(OUT)
    df.to_csv(OUT, index=False)
    print(f"✅ Saved: {OUT} | Rows: {len(df):,} | Customers: {df['CustomerID'].nunique():,}")


if __name__ == "__main__":
    main()
