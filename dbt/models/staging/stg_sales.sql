{{ config(materialized='view') }}

with source as (
    select * from {{ source('staging', 'staging_sales') }}
),

cleaned as (
    select
        transaction_id,
        sale_date::date as sale_date,
        store_id,
        region,
        product_name,
        category,
        quantity::int as quantity,
        unit_price::decimal(10,2) as unit_price,
        discount_rate::decimal(5,4) as discount_rate,
        gross_revenue::decimal(12,2) as gross_revenue,
        discount_amount::decimal(12,2) as discount_amount,
        net_revenue::decimal(12,2) as net_revenue,
        -- Normalize customer type (combine 'RegularCustomer' and 'Regular')
        case 
            when customer_type = 'RegularCustomer' then 'Regular'
            else customer_type
        end as customer_type,
        payment_method,
        loaded_at
    from source
    where transaction_id is not null
      and quantity > 0
      and unit_price > 0
)

select * from cleaned