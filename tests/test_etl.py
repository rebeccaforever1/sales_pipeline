import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import pandas as pd
from etl import (
    normalize_store_id,
    normalize_region,
    parse_date,
    parse_price,
    parse_discount,
    normalize_customer_type,
    normalize_payment,
    transform
)

# ?? normalize_store_id ?????????????????????????????????????????????????

def test_store_id_standard():
    assert normalize_store_id('Store_005') == 'STORE_005'

def test_store_id_uppercase():
    assert normalize_store_id('STORE_005') == 'STORE_005'

def test_store_id_lowercase():
    assert normalize_store_id('store_005') == 'STORE_005'

def test_store_id_with_spaces():
    assert normalize_store_id('Store 005') == 'STORE_005'

def test_store_id_with_prefix():
    assert normalize_store_id('StoreID_005') == 'STORE_005'

def test_store_id_none():
    assert normalize_store_id(None) is None

# ?? normalize_region ???????????????????????????????????????????????????

def test_region_uppercase():
    assert normalize_region('WEST') == 'West'

def test_region_lowercase():
    assert normalize_region('west') == 'West'

def test_region_mixed():
    assert normalize_region('north east') == 'North East'

def test_region_none():
    assert normalize_region(None) is None

# ?? parse_date ?????????????????????????????????????????????????????????

def test_date_iso():
    result = parse_date('2023-01-15')
    assert result.date().isoformat() == '2023-01-15'

def test_date_slash_format():
    result = parse_date('1/16/2023')
    assert result.date().isoformat() == '2023-01-16'

def test_date_dot_format():
    result = parse_date('29.01.2023')
    assert result.date().isoformat() == '2023-01-29'

def test_date_dash_format():
    result = parse_date('22-01-2023')
    assert result.date().isoformat() == '2023-01-22'

def test_date_text_month():
    result = parse_date('26-Jan-23')
    assert result.date().isoformat() == '2023-01-26'

def test_date_invalid():
    assert parse_date('not-a-date') is None

def test_date_none():
    assert parse_date(None) is None

# ?? parse_price ????????????????????????????????????????????????????????

def test_price_with_dollar():
    assert parse_price('1299.99') == 1299.99

def test_price_plain():
    assert parse_price('89.99') == 89.99

def test_price_na():
    assert parse_price('na') is None

def test_price_error():
    assert parse_price('Error') is None

def test_price_none():
    assert parse_price(None) is None

def test_price_empty():
    assert parse_price('') is None

# ?? parse_discount ?????????????????????????????????????????????????????

def test_discount_percent():
    assert parse_discount('10%') == 0.10

def test_discount_decimal():
    assert parse_discount('0.05') == 0.05

def test_discount_integer():
    assert parse_discount('5') == 0.05

def test_discount_zero_percent():
    assert parse_discount('0%') == 0.0

def test_discount_none():
    assert parse_discount(None) == 0.0

def test_discount_empty():
    assert parse_discount('') == 0.0

# ?? normalize_customer_type ????????????????????????????????????????????

def test_customer_regular():
    assert normalize_customer_type('Regular') == 'Regular'

def test_customer_typo():
    assert normalize_customer_type('RegularCustomer') == 'Regular'

def test_customer_premium():
    assert normalize_customer_type('Premium') == 'Premium'

def test_customer_premier():
    assert normalize_customer_type('Premier') == 'Premier'

def test_customer_none():
    assert normalize_customer_type(None) == 'Unknown'

# ?? normalize_payment ??????????????????????????????????????????????????

def test_payment_debit_short():
    assert normalize_payment('Debit') == 'Debit Card'

def test_payment_debit_full():
    assert normalize_payment('Debit Card') == 'Debit Card'

def test_payment_credit():
    assert normalize_payment('Credit Card') == 'Credit Card'

def test_payment_none():
    assert normalize_payment(None) is None

def test_payment_empty():
    assert normalize_payment('') is None

# ?? transform ??????????????????????????????????????????????????????????

def test_transform_clean_row_count():
    df = pd.DataFrame([{
        'date': '2023-01-15',
        'store_id': 'Store_005',
        'product_name': 'Laptop Ultra X1',
        'quantity': '2',
        'price': '.99',
        'customer_type': 'Regular',
        'payment_method': 'Credit Card',
        'transaction_id': 'TRX-001',
        'discount_': '0%',
        'region': 'West'
    }])
    clean, rejected = transform(df)
    assert len(clean) == 1
    assert len(rejected) == 0

def test_transform_rejects_missing_price():
    df = pd.DataFrame([{
        'date': '2023-01-15',
        'store_id': 'Store_005',
        'product_name': 'Laptop Ultra X1',
        'quantity': '2',
        'price': 'na',
        'customer_type': 'Regular',
        'payment_method': 'Credit Card',
        'transaction_id': 'TRX-001',
        'discount_': '0%',
        'region': 'West'
    }])
    clean, rejected = transform(df)
    assert len(clean) == 0
    assert len(rejected) == 1
    assert 'price' in rejected.iloc[0]['rejection_reason']

def test_transform_rejects_zero_quantity():
    df = pd.DataFrame([{
        'date': '2023-01-15',
        'store_id': 'Store_005',
        'product_name': 'Laptop Ultra X1',
        'quantity': '0',
        'price': '1299.99',
        'customer_type': 'Regular',
        'payment_method': 'Credit Card',
        'transaction_id': 'TRX-001',
        'discount_': '0%',
        'region': 'West'
    }])
    clean, rejected = transform(df)
    assert len(clean) == 0
    assert len(rejected) == 1

def test_transform_revenue_calculation():
    df = pd.DataFrame([{
        'date': '2023-01-15',
        'store_id': 'Store_005',
        'product_name': 'Laptop Ultra X1',
        'quantity': '2',
        'price': '100.00',
        'customer_type': 'Regular',
        'payment_method': 'Credit Card',
        'transaction_id': 'TRX-001',
        'discount_': '10%',
        'region': 'West'
    }])
    clean, rejected = transform(df)
    assert len(clean) == 1
    assert clean.iloc[0]['revenue'] == 180.00
