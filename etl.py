import os
import re
import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from dateutil import parser as dateutil_parser
from sqlalchemy import create_engine, text

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger(__name__)

# Config
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = os.getenv("DB_PORT", "5432")
DB_USER     = os.getenv("DB_USER", "sales_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "sales_password")
DB_NAME     = os.getenv("DB_NAME", "sales_db")
CSV_FILE    = os.getenv("CSV_FILE", "/app/data/sales_data.csv")
DB_URL      = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def normalize_store_id(raw):
    if pd.isna(raw): return None
    s = str(raw).strip().upper()
    digits = re.search(r"\d+", s)
    if digits:
        return f"STORE_{digits.group().zfill(3)}"
    return s

def normalize_region(raw):
    if pd.isna(raw): return None
    return str(raw).strip().title()

def parse_date(raw):
    if pd.isna(raw): return None
    try:
        return dateutil_parser.parse(str(raw).strip(), dayfirst=False)
    except:
        return None

def parse_price(raw):
    if pd.isna(raw): return None
    cleaned = str(raw).strip().replace("$", "").replace(",", "")
    try:
        return float(cleaned)
    except:
        return None

def parse_discount(raw):
    if pd.isna(raw): return 0.0
    s = str(raw).strip()
    if s == "": return 0.0
    if "%" in s:
        try:
            return float(s.replace("%", "")) / 100.0
        except:
            return 0.0
    try:
        val = float(s)
        return val / 100.0 if val > 1 else val
    except:
        return 0.0

def normalize_customer_type(raw):
    if pd.isna(raw): return "Unknown"
    s = str(raw).strip()
    mapping = {
        "regular": "Regular",
        "regularcustomer": "Regular",
        "premium": "Premium",
        "premier": "Premier",
    }
    return mapping.get(s.lower(), s)

def normalize_payment(raw):
    if pd.isna(raw) or str(raw).strip() == "": return None
    s = str(raw).strip()
    if s.lower() == "debit": return "Debit Card"
    return s

def extract(csv_path):
    log.info(f"Reading CSV from {csv_path}")
    if not Path(csv_path).exists():
        log.error(f"CSV not found: {csv_path}")
        sys.exit(1)
    df = pd.read_csv(csv_path, dtype=str, skipinitialspace=True)
    df.columns = (df.columns.str.strip().str.lower()
                  .str.replace(r"[\s%]+", "_", regex=True)
                  .str.replace(r"[^a-z0-9_]", "", regex=True))
    log.info(f"Loaded {len(df)} rows")
    return df

def transform(df):
    log.info("Cleaning data...")
    rows_clean, rows_rejected = [], []

    for idx, row in df.iterrows():
        reasons = []
        parsed_date   = parse_date(row.get("date"))
        store_id      = normalize_store_id(row.get("store_id"))
        product_name  = str(row.get("product_name", "")).strip() if pd.notna(row.get("product_name")) else None
        customer_type = normalize_customer_type(row.get("customer_type"))
        payment       = normalize_payment(row.get("payment_method"))
        region        = normalize_region(row.get("region"))
        transaction_id= str(row.get("transaction_id", "")).strip() if pd.notna(row.get("transaction_id")) else None
        price         = parse_price(row.get("price"))
        discount      = parse_discount(row.get("discount_"))

        raw_qty = row.get("quantity", "")
        try:
            quantity = int(float(str(raw_qty).strip())) if pd.notna(raw_qty) and str(raw_qty).strip() != "" else None
        except:
            quantity = None

        if parsed_date is None: reasons.append("unparseable date")
        if price is None:       reasons.append("missing or invalid price")
        elif price <= 0:        reasons.append("price must be positive")
        if quantity is None:    reasons.append("missing quantity")
        elif quantity < 1:      reasons.append("quantity less than 1")
        if not product_name:    reasons.append("missing product name")

        if reasons:
            rows_rejected.append({**row.to_dict(), "rejection_reason": "; ".join(reasons), "loaded_at": datetime.utcnow()})
        else:
            revenue = round(price * quantity * (1 - (discount or 0.0)), 2)
            rows_clean.append({
                "transaction_id": transaction_id,
                "sale_date":      parsed_date.date(),
                "store_id":       store_id,
                "product_name":   product_name,
                "quantity":       quantity,
                "unit_price":     price,
                "discount_pct":   discount or 0.0,
                "revenue":        revenue,
                "customer_type":  customer_type,
                "payment_method": payment,
                "region":         region,
                "loaded_at":      datetime.utcnow(),
            })

    log.info(f"{len(rows_clean)} rows clean, {len(rows_rejected)} rejected")
    return pd.DataFrame(rows_clean), pd.DataFrame(rows_rejected)

def load(df_clean, df_rejected, db_url):
    log.info("Connecting to PostgreSQL...")
    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw_data"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS audit"))
    if not df_clean.empty:
        df_clean.to_sql("stg_sales", engine, schema="raw_data", if_exists="replace", index=False)
        log.info("Loaded stg_sales")
    if not df_rejected.empty:
        df_rejected.to_sql("rejected_rows", engine, schema="audit", if_exists="replace", index=False)
        log.info("Loaded rejected_rows")
    pd.DataFrame([{
        "run_at": datetime.utcnow(),
        "rows_loaded": len(df_clean),
        "rows_rejected": len(df_rejected),
        "status": "success"
    }]).to_sql("pipeline_runs", engine, schema="audit", if_exists="append", index=False)

def main():
    log.info("ETL started")
    try:
        raw = extract(CSV_FILE)
        clean, rejected = transform(raw)
        load(clean, rejected, DB_URL)
        log.info("ETL completed successfully")
        sys.exit(0)
    except Exception as e:
        log.exception(f"ETL failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()