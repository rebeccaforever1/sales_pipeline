#!/usr/bin/env python3
"""
ETL Pipeline - Synthetic Data Generation and Loading
Generates sales data matching the sample CSV patterns and loads to PostgreSQL
"""

import pandas as pd
import numpy as np
import psycopg2
from sqlalchemy import create_engine
import os
import logging
import sys
from datetime import datetime, timedelta
import random
from faker import Faker

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Faker for realistic data
fake = Faker()
np.random.seed(42)
random.seed(42)

# Product catalog (matching your sample CSV)
PRODUCT_CATALOG = {
    'Laptop Ultra X1': {'price': 1299.99, 'category': 'Computing'},
    'Desktop PC Gaming': {'price': 1499.99, 'category': 'Computing'},
    'Smartphone X12': {'price': 799.99, 'category': 'Mobile'},
    'Tablet Pro': {'price': 649.99, 'category': 'Mobile'},
    'Wireless Headphones': {'price': 89.99, 'category': 'Audio'},
    'Bluetooth Speaker': {'price': 129.99, 'category': 'Audio'},
    'Monitor, 27-inch': {'price': 349.99, 'category': 'Peripherals'},
    'Wireless Mouse': {'price': 49.99, 'category': 'Peripherals'},
    'External SSD 1TB': {'price': 159.99, 'category': 'Storage'},
    'USB-C Cable 2m': {'price': 19.99, 'category': 'Accessories'},
    'Laptop Stand': {'price': 29.99, 'category': 'Accessories'},
    'Wireless Keyboard': {'price': 79.99, 'category': 'Peripherals'},
    'Power Bank 20000mAh': {'price': 59.99, 'category': 'Accessories'},
    'Smart Watch Series 7': {'price': 299.99, 'category': 'Wearables'},
    'Airpods Pro': {'price': 249.99, 'category': 'Audio'}
}

# Store configuration (6 stores across regions)
STORES = [
    {'store_id': 'STORE_005', 'region': 'West'},
    {'store_id': 'STORE_006', 'region': 'East'},
    {'store_id': 'STORE_007', 'region': 'South'},
    {'store_id': 'STORE_008', 'region': 'North'},
    {'store_id': 'STORE_009', 'region': 'Central'},
    {'store_id': 'STORE_010', 'region': 'West'}
]

# Customer types (from your sample)
CUSTOMER_TYPES = ['Regular', 'Premium', 'Enterprise', 'RegularCustomer']
CUSTOMER_TYPE_MAP = {'RegularCustomer': 'Regular'}  # Normalize later

# Payment methods (from your sample)
PAYMENT_METHODS = ['Credit Card', 'Debit Card', 'Cash', 'Apple Pay', 'PayPal']


def generate_sales_data(num_rows=5000):
    """Generate synthetic sales data matching sample patterns"""
    
    logger.info(f"Generating {num_rows} synthetic sales records")
    
    data = []
    
    for i in range(num_rows):
        # Generate random date within last year
        days_ago = random.randint(0, 365)
        sale_date = datetime.now() - timedelta(days=days_ago)
        
        # Select random store
        store = random.choice(STORES)
        
        # Select random product
        product_name = random.choice(list(PRODUCT_CATALOG.keys()))
        product = PRODUCT_CATALOG[product_name]
        
        # Quantity (weighted toward small orders)
        quantity = random.choices(
            [1, 2, 3, 4, 5, 10],
            weights=[0.4, 0.3, 0.15, 0.08, 0.05, 0.02]
        )[0]
        
        # Discount (mostly 0, occasional promotions)
        discount = random.choices(
            [0, 0.05, 0.10, 0.15, 0.20],
            weights=[0.6, 0.2, 0.12, 0.05, 0.03]
        )[0]
        
        # Customer type
        customer_type_raw = random.choices(
            CUSTOMER_TYPES,
            weights=[0.6, 0.25, 0.1, 0.05]
        )[0]
        
        # Normalize customer type
        customer_type = CUSTOMER_TYPE_MAP.get(customer_type_raw, customer_type_raw)
        
        # Payment method
        payment_method = random.choice(PAYMENT_METHODS)
        
        # Generate transaction ID
        transaction_id = f"TRX-{100000 + i:06d}"
        
        # Calculate derived fields
        gross_revenue = quantity * product['price']
        discount_amount = gross_revenue * discount
        net_revenue = gross_revenue - discount_amount
        
        data.append({
            'transaction_id': transaction_id,
            'sale_date': sale_date,
            'store_id': store['store_id'],
            'region': store['region'],
            'product_name': product_name,
            'category': product['category'],
            'quantity': quantity,
            'unit_price': product['price'],
            'discount_rate': discount,
            'gross_revenue': gross_revenue,
            'discount_amount': discount_amount,
            'net_revenue': net_revenue,
            'customer_type': customer_type,
            'payment_method': payment_method
        })
    
    df = pd.DataFrame(data)
    
    # Introduce some data quality issues (like the real CSV)
    # Add 2% rows with issues to test validation
    issue_indices = np.random.choice(df.index, size=int(len(df) * 0.02), replace=False)
    
    for idx in issue_indices:
        issue_type = random.choice(['null_transaction', 'zero_quantity', 'null_price'])
        if issue_type == 'null_transaction':
            df.at[idx, 'transaction_id'] = None
        elif issue_type == 'zero_quantity':
            df.at[idx, 'quantity'] = 0
        else:
            df.at[idx, 'unit_price'] = None
    
    logger.info(f"Generated {len(df)} rows (including {len(issue_indices)} test issues)")
    
    return df


def clean_and_validate(df):
    """Clean data and filter invalid records"""
    
    original_count = len(df)
    
    # Filter invalid records
    valid_mask = (
        df['transaction_id'].notna() &
        (df['quantity'] > 0) &
        df['unit_price'].notna() &
        (df['unit_price'] > 0)
    )
    
    df_clean = df[valid_mask].copy()
    rejected_count = original_count - len(df_clean)
    
    if rejected_count > 0:
        logger.warning(f"Rejected {rejected_count} rows with data quality issues")
        
        # Log sample of rejected rows for debugging
        rejected_sample = df[~valid_mask].head(3)
        for idx, row in rejected_sample.iterrows():
            logger.warning(f"  Rejected row: {row.get('transaction_id', 'NO_ID')} - quantity={row.get('quantity')}, price={row.get('unit_price')}")
    
    # Add loaded_at timestamp
    df_clean['loaded_at'] = datetime.now()
    
    logger.info(f"Clean data: {len(df_clean)} rows ready for loading")
    
    return df_clean


def load_to_postgres(df):
    """Load cleaned data to PostgreSQL staging table"""
    
    # Get connection parameters from environment
    pg_host = os.environ.get('PG_HOST', 'localhost')
    pg_user = os.environ.get('PG_USER', 'sales_user')
    pg_pass = os.environ.get('PG_PASSWORD', 'sales_password')
    pg_db = os.environ.get('PG_DB', 'sales_db')
    
    connection_string = f"postgresql://{pg_user}:{pg_pass}@{pg_host}:5432/{pg_db}"
    engine = create_engine(connection_string)
    
    # Create staging table if not exists
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS staging_sales (
        id SERIAL PRIMARY KEY,
        transaction_id VARCHAR(50),
        sale_date TIMESTAMP,
        store_id VARCHAR(20),
        region VARCHAR(50),
        product_name VARCHAR(200),
        category VARCHAR(100),
        quantity INTEGER,
        unit_price DECIMAL(10,2),
        discount_rate DECIMAL(5,4),
        gross_revenue DECIMAL(12,2),
        discount_amount DECIMAL(12,2),
        net_revenue DECIMAL(12,2),
        customer_type VARCHAR(50),
        payment_method VARCHAR(50),
        loaded_at TIMESTAMP
    )
    """
    
    with engine.connect() as conn:
        conn.execute(create_table_sql)
        conn.commit()
    
    # Load data (replace existing for idempotency)
    df.to_sql('staging_sales', engine, if_exists='replace', index=False)
    
    # Verify load
    with engine.connect() as conn:
        result = conn.execute("SELECT COUNT(*) FROM staging_sales")
        count = result.scalar()
        logger.info(f"Successfully loaded {count} records to staging_sales")
    
    engine.dispose()


def main():
    """Main ETL pipeline"""
    logger.info("=" * 50)
    logger.info("Starting ETL Pipeline")
    logger.info("=" * 50)
    
    try:
        # Generate synthetic data
        df_raw = generate_sales_data(num_rows=5000)
        
        # Clean and validate
        df_clean = clean_and_validate(df_raw)
        
        # Load to PostgreSQL
        load_to_postgres(df_clean)
        
        logger.info("=" * 50)
        logger.info("ETL Pipeline completed successfully")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"ETL Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()