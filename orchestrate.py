import subprocess
import sys
import time
import logging
import re
import os
import psycopg2
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "user":     "sales_user",
    "password": "sales_password",
    "dbname":   "sales_db",
}

def run_command(cmd, description):
    logger.info(f"STARTING: {description}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    stdout = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout)
    if result.returncode == 0:
        logger.info(f"SUCCESS: {description}")
        if stdout.strip():
            logger.info(stdout.strip()[:800])
        return True, stdout
    else:
        logger.error(f"FAILED: {description}")
        logger.error(result.stderr[:500])
        return False, result.stderr

def wait_for_postgres(retries=30):
    logger.info("Waiting for PostgreSQL to be ready...")
    for i in range(retries):
        result = subprocess.run(
            'docker compose exec postgres pg_isready -U sales_user',
            shell=True, capture_output=True, text=True
        )
        if result.returncode == 0:
            logger.info("PostgreSQL is ready")
            return True
        logger.info(f"Not ready yet, retry {i+1}/{retries}...")
        time.sleep(3)
    logger.error("PostgreSQL never became ready")
    return False

def write_metadata(start_time, status, rows_loaded, rows_rejected,
                   dbt_models_passed, dbt_tests_passed, failure_reason):
    duration = round(time.time() - start_time, 2)
    fr = failure_reason if failure_reason else "none"
    cmd = (
        f'docker compose exec postgres psql -U sales_user -d sales_db -c '
        f'"INSERT INTO audit.pipeline_runs_v2 '
        f'(run_at, duration_seconds, rows_loaded, rows_rejected, dbt_models_passed, dbt_tests_passed, status, failure_reason) '
        f'VALUES (NOW(), {duration}, {rows_loaded}, {rows_rejected}, {dbt_models_passed}, {dbt_tests_passed}, \'{status}\', \'{fr}\');"'
    )
    ok, _ = run_command(cmd, "Writing pipeline metadata")
    if ok:
        logger.info(f"Metadata recorded — duration: {duration}s, status: {status}")

def parse_dbt_counts(output, keyword):
    match = re.search(rf'PASS=(\d+)', output)
    return int(match.group(1)) if match else 0

def main():
    start_time = time.time()
    rows_loaded = 0
    rows_rejected = 0
    dbt_models_passed = 0
    dbt_tests_passed = 0
    failure_reason = None

    logger.info("=" * 60)
    logger.info("SALES PIPELINE STARTING")
    logger.info(f"Start time: {datetime.now()}")
    logger.info("=" * 60)

    ok, _ = run_command("docker compose up -d postgres", "Starting PostgreSQL")
    if not ok:
        write_metadata(start_time, "failed", 0, 0, 0, 0, "postgres failed to start")
        sys.exit(1)

    if not wait_for_postgres():
        write_metadata(start_time, "failed", 0, 0, 0, 0, "postgres never became ready")
        sys.exit(1)

    ok, etl_out = run_command("docker compose run --rm etl", "Python ETL")
    if not ok:
        write_metadata(start_time, "failed", 0, 0, 0, 0, "ETL failed")
        sys.exit(1)

    # Parse ETL row counts from output
    m = re.search(r'(\d+) rows clean, (\d+) rejected', etl_out)
    if m:
        rows_loaded   = int(m.group(1))
        rows_rejected = int(m.group(2))

    ok, dbt_out = run_command("docker compose run --rm dbt", "dbt models")
    if not ok:
        write_metadata(start_time, "failed", rows_loaded, rows_rejected, 0, 0, "dbt models failed")
        sys.exit(1)
    dbt_models_passed = parse_dbt_counts(dbt_out, "PASS")

    ok, test_out = run_command(
        'docker compose run --rm dbt dbt test --profiles-dir /app/dbt --project-dir /app/dbt',
        "dbt tests"
    )
    if not ok:
        logger.warning("Some tests failed - check data quality")
    dbt_tests_passed = parse_dbt_counts(test_out, "PASS")

    run_command(
        'docker compose exec postgres psql -U sales_user -d sales_db -c "SELECT COUNT(*) FROM analytics.daily_sales_metrics;"',
        "Final verification"
    )

    write_metadata(start_time, "success", rows_loaded, rows_rejected,
                   dbt_models_passed, dbt_tests_passed, None)

    elapsed = round(time.time() - start_time, 2)
    logger.info("=" * 60)
    logger.info(f"PIPELINE COMPLETE - Duration: {elapsed}s")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()