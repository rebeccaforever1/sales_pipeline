import subprocess
import json
import re

def query(sql):
    cmd = f'docker compose exec postgres psql -U sales_user -d sales_db -t -A -F "," -c "{sql}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    rows = [r.strip() for r in result.stdout.strip().split('\n') if r.strip()]
    return rows

print("Exporting data...")

# Revenue by region
region_rows = query("SELECT region, ROUND(SUM(total_net_revenue)::numeric,2) FROM analytics.daily_sales_metrics GROUP BY region ORDER BY 2 DESC;")
region_data = {}
for r in region_rows:
    parts = r.split(',')
    if len(parts) == 2:
        region_data[parts[0]] = float(parts[1])

# Revenue by store
store_rows = query("SELECT store_id, ROUND(SUM(total_net_revenue)::numeric,2) FROM analytics.daily_sales_metrics GROUP BY store_id ORDER BY 1;")
store_data = {}
for r in store_rows:
    parts = r.split(',')
    if len(parts) == 2:
        store_data[parts[0]] = float(parts[1])

# Daily revenue trend
daily_rows = query("SELECT sale_date::text, ROUND(SUM(total_net_revenue)::numeric,2) FROM analytics.daily_sales_metrics GROUP BY sale_date ORDER BY sale_date;")
daily_data = {}
for r in daily_rows:
    parts = r.split(',')
    if len(parts) == 2:
        daily_data[parts[0]] = float(parts[1])

# Top products
product_rows = query("SELECT product_name, ROUND(SUM(revenue)::numeric,2) FROM analytics.stg_sales GROUP BY product_name ORDER BY 2 DESC LIMIT 8;")
product_data = {}
for r in product_rows:
    parts = r.rsplit(',', 1)
    if len(parts) == 2:
        product_data[parts[0]] = float(parts[1])

# Pipeline runs
run_rows = query("SELECT run_at::text, duration_seconds, rows_loaded, rows_rejected, dbt_models_passed, dbt_tests_passed, status FROM audit.pipeline_runs_v2 ORDER BY run_at DESC LIMIT 5;")
run_data = []
for r in run_rows:
    parts = r.split(',')
    if len(parts) == 7:
        run_data.append({
            "run_at": parts[0],
            "duration": parts[1],
            "rows_loaded": parts[2],
            "rows_rejected": parts[3],
            "models_passed": parts[4],
            "tests_passed": parts[5],
            "status": parts[6]
        })

# Summary stats
total_rows = query("SELECT COUNT(*) FROM analytics.stg_sales;")
total_revenue = query("SELECT ROUND(SUM(revenue)::numeric,2) FROM analytics.stg_sales;")
rejected_rows = query("SELECT COUNT(*) FROM audit.rejected_rows;")

data = {
    "region": region_data,
    "store": store_data,
    "daily": daily_data,
    "products": product_data,
    "pipeline_runs": run_data,
    "summary": {
        "total_transactions": total_rows[0] if total_rows else 0,
        "total_revenue": total_revenue[0] if total_revenue else 0,
        "rejected_rows": rejected_rows[0] if rejected_rows else 0
    }
}

with open('dashboard/data.json', 'w') as f:
    json.dump(data, f, indent=2)

print("Data exported to dashboard/data.json")
