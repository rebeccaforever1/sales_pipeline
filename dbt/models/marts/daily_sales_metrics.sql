{{ config(
    materialized='incremental',
    unique_key=['sale_date', 'store_id', 'region', 'customer_type'],
    incremental_strategy='delete+insert'
) }}

with daily_aggregates as (
    select
        sale_date,
        store_id,
        region,
        customer_type,
        count(distinct transaction_id) as transaction_count,
        sum(quantity) as total_units_sold,
        sum(unit_price * quantity) as total_gross_revenue,
        sum(revenue) as total_net_revenue,
        avg(unit_price) as avg_unit_price,
        avg(discount_pct) as avg_discount_rate,
        count(case when discount_pct > 0 then 1 end) as discounted_transactions
    from {{ ref('int_sales_enriched') }}

    {% if is_incremental() %}
        where sale_date > (select max(sale_date) from {{ this }})
    {% endif %}
    group by 1, 2, 3, 4
),
with_metrics as (
    select
        *,
        lag(total_net_revenue, 1) over (
            partition by store_id, customer_type
            order by sale_date
        ) as prev_day_revenue,
        avg(total_net_revenue) over (
            partition by store_id
            order by sale_date
            rows between 6 preceding and current row
        ) as revenue_7day_avg,
        round(discounted_transactions * 100.0 / nullif(transaction_count, 0), 2) as discount_pct
    from daily_aggregates
)
select
    sale_date,
    store_id,
    region,
    customer_type,
    transaction_count,
    total_units_sold,
    round(total_gross_revenue::numeric, 2) as total_gross_revenue,
    round(total_net_revenue::numeric, 2) as total_net_revenue,
    round(avg_unit_price::numeric, 2) as avg_unit_price,
    round(avg_discount_rate::numeric * 100, 2) as avg_discount_percent,
    discount_pct,
    round(prev_day_revenue::numeric, 2) as prev_day_revenue,
    case
        when prev_day_revenue is null then null
        else round(((total_net_revenue - prev_day_revenue) * 100.0 / nullif(prev_day_revenue, 0))::numeric, 2)
    end as revenue_daily_pct_change,
    round(revenue_7day_avg::numeric, 2) as revenue_7day_avg,
    extract(dow from sale_date) as day_of_week,
    to_char(sale_date, 'Day') as day_name
from with_metrics
order by sale_date desc, store_id, customer_type
