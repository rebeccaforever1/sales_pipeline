#!/usr/bin/env python3
"""
Pipeline Orchestration - Runs ETL and dBT in correct order
"""

import subprocess
import sys
import time
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_command(cmd, description, shell=True):
    """Execute a shell command and handle errors"""
    logger.info(f"▶ {description}")
    
    result = subprocess.run(cmd, shell=shell, capture_output=True, text=True)
    
    if result.returncode == 0:
        logger.info(f"✓ {description} completed")
        if result.stdout:
            logger.debug(f"Output: {result.stdout[:200]}")
        return True
    else:
        logger.error(f"✗ {description} failed")
        logger.error(f"Error: {result.stderr[:500]}")
        return False


def main():
    """Main orchestration flow"""
    start_time = time.time()
    
    logger.info("=" * 60)
    logger.info("SALES PIPELINE ORCHESTRATION STARTING")
    logger.info(f"Start time: {datetime.now()}")
    logger.info("=" * 60)
    
    # Step 1: Ensure PostgreSQL is running
    if not run_command("docker-compose up -d postgres", "Starting PostgreSQL"):
        sys.exit(1)
    
    # Wait for PostgreSQL to be fully ready
    logger.info("Waiting for PostgreSQL to be ready...")
    time.sleep(5)
    
    # Step 2: Run ETL to generate and load data
    if not run_command("docker-compose run --rm python-etl", "Python ETL (Generate & Load Data)"):
        sys.exit(1)
    
    # Step 3: Run dBT models
    if not run_command("docker exec sales_dbt dbt run", "dBT Transformations"):
        sys.exit(1)
    
    # Step 4: Run dBT tests
    if not run_command("docker exec sales_dbt dbt test", "dBT Data Quality Tests"):
        logger.warning("Tests failed - continuing but check data quality")
    
    # Step 5: Verify final output
    verify_sql = "SELECT COUNT(*) FROM analytics.daily_sales_metrics"
    if not run_command(
        f"docker exec sales_postgres psql -U sales_user -d sales_db -tAc \"{verify_sql}\"",
        "Final Verification"
    ):
        logger.warning("Could not verify final table")
    
    elapsed = time.time() - start_time
    
    logger.info("=" * 60)
    logger.info(f"PIPELINE COMPLETE - Duration: {elapsed:.2f} seconds")
    logger.info("=" * 60)
    logger.info("Query results with:")
    logger.info("  docker exec -it sales_postgres psql -U sales_user -d sales_db")
    logger.info("  SELECT * FROM analytics.daily_sales_metrics LIMIT 10;")


if __name__ == "__main__":
    main()
