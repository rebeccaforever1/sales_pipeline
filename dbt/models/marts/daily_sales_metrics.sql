{{ config(materialized='table') }}

with daily_aggregates as (
    select
        sale_date,
        store_id,
        region,
        customer_type,
        count(distinct transaction_id) as transaction_count,
        sum(quantity) as total_units_sold,
        sum(gross_revenue) as total_gross_revenue,
        sum(discount_amount) as total_discounts_given,
        sum(net_revenue) as total_net_revenue,
        avg(unit_price) as avg_unit_price,
        avg(discount_rate) as avg_discount_rate,
        count(case when discount_rate > 0 then 1 end) as discounted_transactions
    from {{ ref('stg_sales') }}
    group by 1, 2, 3, 4
),

with_metrics as (
    select
        *,
        -- Previous day revenue for growth calculation
        lag(total_net_revenue, 1) over (
            partition by store_id, customer_type 
            order by sale_date
        ) as prev_day_revenue,
        
        -- 7-day moving average
        avg(total_net_revenue) over (
            partition by store_id
            order by sale_date
            rows between 6 preceding and current row
        ) as revenue_7day_avg,
        
        -- Discount penetration
        round(discounted_transactions * 100.0 / nullif(transaction_count, 0), 2) as discount_pct
    from daily_aggregates
),

final as (
    select
        sale_date,
        store_id,
        region,
        customer_type,
        transaction_count,
        total_units_sold,
        total_gross_revenue,
        total_discounts_given,
        total_net_revenue,
        round(avg_unit_price, 2) as avg_unit_price,
        round(avg_discount_rate * 100, 2) as avg_discount_percent,
        discount_pct,
        prev_day_revenue,
        case 
            when prev_day_revenue is null then null
            else round((total_net_revenue - prev_day_revenue) * 100.0 / nullif(prev_day_revenue, 0), 2)
        end as revenue_daily_pct_change,
        round(revenue_7day_avg, 2) as revenue_7day_avg,
        -- Day of week for trend analysis
        extract(dow from sale_date) as day_of_week,
        to_char(sale_date, 'Day') as day_name
    from with_metrics
)

select * from final
order by sale_date desc, store_id, customer_type