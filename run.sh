#!/bin/bash
set -e

echo "Starting Sales Pipeline..."
echo ""

# Run orchestration
python orchestrate.py

# Check if successful
if [ $? -eq 0 ]; then
    echo ""
    echo "Pipeline completed successfully!"
    echo ""
    echo "Query the results:"
    echo "   docker exec -it sales_postgres psql -U sales_user -d sales_db"
    echo "   SELECT * FROM analytics.daily_sales_metrics LIMIT 10;"
else
    echo "Pipeline failed. Check logs above."
    exit 1
fi