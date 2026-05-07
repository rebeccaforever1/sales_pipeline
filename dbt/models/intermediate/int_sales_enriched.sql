{{ config(
    materialized='incremental',
    unique_key='transaction_id',
    incremental_strategy='delete+insert'
) }}

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
    loaded_at,
    case
        when product_name ilike '%laptop%'     then 'Computers'
        when product_name ilike '%desktop%'    then 'Computers'
        when product_name ilike '%tablet%'     then 'Computers'
        when product_name ilike '%smartphone%' then 'Mobile'
        when product_name ilike '%airpods%'    then 'Mobile'
        when product_name ilike '%watch%'      then 'Mobile'
        when product_name ilike '%headphone%'  then 'Audio'
        when product_name ilike '%speaker%'    then 'Audio'
        when product_name ilike '%ssd%'        then 'Storage'
        when product_name ilike '%monitor%'    then 'Displays'
        else 'Accessories'
    end as product_category,
    case
        when unit_price >= 1000 then 'Premium'
        when unit_price >= 200  then 'Mid-Range'
        when unit_price >= 50   then 'Standard'
        else 'Budget'
    end as price_tier,
    case when discount_pct > 0 then true else false end as is_discounted,
    round((unit_price * quantity * discount_pct)::numeric, 2) as discount_amount,
    extract(year  from sale_date)::integer as sale_year,
    extract(month from sale_date)::integer as sale_month,
    case
        when extract(month from sale_date) <= 3  then 'Q1'
        when extract(month from sale_date) <= 6  then 'Q2'
        when extract(month from sale_date) <= 9  then 'Q3'
        else 'Q4'
    end as sale_quarter
from {{ ref('stg_sales') }}

{% if is_incremental() %}
    where loaded_at > (select max(loaded_at) from {{ this }})
{% endif %}
