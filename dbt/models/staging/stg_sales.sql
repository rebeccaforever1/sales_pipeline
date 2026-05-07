{{ config(materialized='view') }}

select
    transaction_id,
    sale_date,
    store_id,
    region,
    product_name,
    quantity,
    unit_price,
    discount_pct,
    revenue,
    customer_type,
    payment_method,
    loaded_at
from {{ source('raw_data', 'stg_sales') }}
