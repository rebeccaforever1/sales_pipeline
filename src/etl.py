"""
ETL Pipeline - Reads existing CSV, cleans, loads to PostgreSQL
No synthetic generation - uses your actual sales_data.csv
"""

import pandas as pd
import numpy as np
import os
import re
import logging
from datetime import datetime
from pathlib import Path
import requests
from sqlalchemy import create_engine

logger = logging.getLogger(__name__)


class CSVLoader:
    """Handles loading CSV from multiple sources"""
    
    def __init__(self, local_path=None, github_url=None):
        self.local_path = local_path or r"C:\Users\rebec\Documents\demo\sales_data.csv"
        self.github_url = github_url or "https://raw.githubusercontent.com/rebeccaforever1/sales_pipeline/main/data/raw/sales_data.csv"
    
    def load(self):
        """Load CSV from first available source"""
        
        # Try local path first
        if os.path.exists(self.local_path):
            logger.info(f"Loading from local: {self.local_path}")
            return pd.read_csv(self.local_path)
        
        # Try GitHub as fallback
        try:
            logger.info(f"Loading from GitHub: {self.github_url}")
            return pd.read_csv(self.github_url)
        except Exception as e:
            logger.error(f"Could not load from GitHub: {e}")
            raise FileNotFoundError(f"No data source available at {self.local_path} or {self.github_url}")


class DateParser:
    """Handles the 8+ date formats in your CSV"""
    
    DATE_FORMATS = [
        '%Y-%m-%d', '%m/%d/%Y', '%Y/%m/%d', '%m-%d-%Y',
        '%d-%m-%Y', '%d/%m/%Y', '%d.%m.%Y', '%d-%b-%y',
        '%m/%d/%y', '%Y-%m-%d'
    ]
    
    @classmethod
    def parse(cls, date_str):
        """Try multiple formats until one works"""
        if pd.isna(date_str):
            return None
        
        date_str = str(date_str).strip()
        
        for fmt in cls.DATE_FORMATS:
            try:
                return pd.to_datetime(date_str, format=fmt).date()
            except (ValueError, TypeError):
                continue
        
        # Last resort: let pandas guess
        try:
            return pd.to_datetime(date_str).date()
        except:
            logger.warning(f"Could not parse date: {date_str}")
            return None


class DataCleaner:
    """Cleans the messy CSV data"""
    
    def __init__(self, df):
        self.df = df.copy()
    
    def clean_column_names(self):
        """Standardize column names to snake_case"""
        self.df.columns = [
            col.strip().lower().replace(' ', '_').replace('%', 'percent')
            for col in self.df.columns
        ]
        return self
    
    def clean_dates(self):
        """Parse all date formats"""
        date_columns = [col for col in self.df.columns if 'date' in col.lower()]
        for col in date_columns:
            self.df[f'{col}_cleaned'] = self.df[col].apply(DateParser.parse)
        return self
    
    def clean_prices(self):
        """Remove $ signs, handle 'na', convert to float"""
        price_columns = [col for col in self.df.columns if 'price' in col.lower()]
        
        for col in price_columns:
            def clean_price(val):
                if pd.isna(val):
                    return None
                val_str = str(val).strip()
                if val_str.lower() in ['na', 'error', '']:
                    return None
                cleaned = re.sub(r'[^\d.-]', '', val_str)
                try:
                    return float(cleaned)
                except:
                    return None
            
            self.df[f'{col}_cleaned'] = self.df[col].apply(clean_price)
        
        return self
    
    def clean_discounts(self):
        """Convert '5%', '0.05', '5' to decimal 0.05"""
        discount_cols = [col for col in self.df.columns if 'discount' in col.lower()]
        
        for col in discount_cols:
            def clean_discount(val):
                if pd.isna(val):
                    return 0.0
                val_str = str(val).strip()
                if val_str == '':
                    return 0.0
                if '%' in val_str:
                    val_str = val_str.replace('%', '')
                    try:
                        return float(val_str) / 100
                    except:
                        pass
                try:
                    return float(val_str)
                except:
                    return 0.0
            
            self.df[f'{col}_cleaned'] = self.df[col].apply(clean_discount)
        
        return self
    
    def clean_store_ids(self):
        """Standardize STORE_005, Store 005, STORE_005 to STORE_005"""
        store_cols = [col for col in self.df.columns if 'store' in col.lower()]
        
        for col in store_cols:
            def standardize(store_str):
                if pd.isna(store_str):
                    return None
                store_str = str(store_str).strip().upper()
                match = re.search(r'(\d+)', store_str)
                if match:
                    return f"STORE_{match.group(1).zfill(3)}"
                return store_str
            
            self.df[f'{col}_cleaned'] = self.df[col].apply(standardize)
        
        return self
    
    def clean_regions(self):
        """Standardize region names to uppercase"""
        region_cols = [col for col in self.df.columns if 'region' in col.lower()]
        
        for col in region_cols:
            self.df[f'{col}_cleaned'] = self.df[col].str.strip().str.upper()
        
        return self
    
    def calculate_derived_columns(self):
        """Add revenue calculations"""
        # Find quantity column
        qty_col = next((col for col in self.df.columns if 'quantity' in col.lower()), None)
        price_col = next((col for col in self.df.columns if 'price' in col.lower() and 'cleaned' in col), None)
        discount_col = next((col for col in self.df.columns if 'discount' in col.lower() and 'cleaned' in col), None)
        
        if qty_col and price_col:
            self.df['gross_revenue'] = pd.to_numeric(self.df[qty_col], errors='coerce') * self.df[price_col]
            
            if discount_col:
                self.df['discount_amount'] = self.df['gross_revenue'] * self.df[discount_col]
                self.df['net_revenue'] = self.df['gross_revenue'] - self.df['discount_amount']
            else:
                self.df['discount_amount'] = 0
                self.df['net_revenue'] = self.df['gross_revenue']
        
        return self
    
    def filter_valid_rows(self):
        """Remove rows with critical missing data"""
        # Build mask based on available columns
        mask = pd.Series([True] * len(self.df))
        
        # Check for null transaction IDs
        transaction_col = next((col for col in self.df.columns if 'transaction' in col.lower()), None)
        if transaction_col:
            mask &= self.df[transaction_col].notna()
        
        # Check for zero/negative quantity
        qty_col = next((col for col in self.df.columns if 'quantity' in col.lower()), None)
        if qty_col:
            mask &= pd.to_numeric(self.df[qty_col], errors='coerce') > 0
        
        # Check for null/negative price
        price_col = next((col for col in self.df.columns if 'price' in col.lower() and 'cleaned' in col), None)
        if price_col:
            mask &= self.df[price_col] > 0
        
        rejected = (~mask).sum()
        if rejected > 0:
            logger.warning(f"Filtered out {rejected} invalid rows")
        
        self.df = self.df[mask].copy()
        return self
    
    def get_clean_data(self):
        """Return cleaned DataFrame"""
        return self.df


class PostgresLoader:
    """Loads cleaned data to PostgreSQL"""
    
    def __init__(self, connection_string, table_name='staging_sales'):
        self.connection_string = connection_string
        self.table_name = table_name
        self.engine = create_engine(connection_string)
    
    def create_table_if_not_exists(self):
        """Create staging table with appropriate schema"""
        create_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} (
            id SERIAL PRIMARY KEY,
            transaction_id VARCHAR(50),
            sale_date DATE,
            store_id VARCHAR(20),
            product_name VARCHAR(200),
            quantity INTEGER,
            unit_price DECIMAL(10,2),
            discount_rate DECIMAL(5,4),
            gross_revenue DECIMAL(12,2),
            discount_amount DECIMAL(12,2),
            net_revenue DECIMAL(12,2),
            customer_type VARCHAR(50),
            payment_method VARCHAR(50),
            region VARCHAR(50),
            loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        with self.engine.connect() as conn:
            conn.execute(create_sql)
            conn.commit()
    
    def load(self, df):
        """Load DataFrame to staging table"""
        self.create_table_if_not_exists()
        
        # Select and rename columns to match schema
        load_df = self._prepare_for_load(df)
        
        load_df.to_sql(self.table_name, self.engine, if_exists='replace', index=False)
        
        # Verify
        with self.engine.connect() as conn:
            result = conn.execute(f"SELECT COUNT(*) FROM {self.table_name}")
            count = result.scalar()
            logger.info(f"Loaded {count} records to {self.table_name}")
        
        return count
    
    def _prepare_for_load(self, df):
        """Map source columns to target schema"""
        # This adapts to whatever columns came from the CSV
        column_mapping = {
            'transaction_id': 'transaction_id',
            'date': 'sale_date',
            'store_id': 'store_id',
            'product_name': 'product_name',
            'quantity': 'quantity',
            'price': 'unit_price',
            'discount': 'discount_rate',
            'customer_type': 'customer_type',
            'payment_method': 'payment_method',
            'region': 'region'
        }
        
        result_df = pd.DataFrame()
        
        for source, target in column_mapping.items():
            # Find column that matches pattern
            matches = [col for col in df.columns if source.replace('_', '') in col.replace('_', '').lower()]
            if matches:
                result_df[target] = df[matches[0]]
            else:
                result_df[target] = None
        
        # Add calculated fields if they exist
        if 'gross_revenue' in df.columns:
            result_df['gross_revenue'] = df['gross_revenue']
        if 'net_revenue' in df.columns:
            result_df['net_revenue'] = df['net_revenue']
        
        return result_df


def run_etl():
    """Main ETL function"""
    logger.info("Starting ETL Pipeline")
    
    # 1. Load CSV
    loader = CSVLoader()
    df_raw = loader.load()
    logger.info(f"Loaded {len(df_raw)} rows from CSV")
    
    # 2. Clean data
    cleaner = DataCleaner(df_raw)
    cleaner.clean_column_names()
    cleaner.clean_dates()
    cleaner.clean_prices()
    cleaner.clean_discounts()
    cleaner.clean_store_ids()
    cleaner.clean_regions()
    cleaner.calculate_derived_columns()
    cleaner.filter_valid_rows()
    
    df_clean = cleaner.get_clean_data()
    logger.info(f"Cleaned data: {len(df_clean)} valid rows")
    
    # 3. Load to PostgreSQL
    from config.settings import config
    pg_loader = PostgresLoader(config.database.connection_string)
    pg_loader.load(df_clean)
    
    logger.info("ETL Pipeline Complete")
    return df_clean


if __name__ == "__main__":
    run_etl()