# Sales Data Pipeline

Containerised data pipeline to read raw sales data from CSV,
clean it, load it into PostgreSQL, and transform it with dbt.

## 

## What it does

1. Python ETL reads example\_sales\_data.csv
2. Cleans messy data (10+ date formats, inconsistent store IDs, bad prices)
3. Loads 43 clean rows into PostgreSQL, logs 8 rejected rows with reasons
4. dbt builds 3 models on top of the raw data
5. 17 data quality tests validate the output

## 

## Architecture

CSV File
|
v
Python ETL (etl.py)

* Reads and cleans raw CSV
* Validates every row
* Loads clean rows to raw\_data.stg\_sales
* Logs rejected rows to audit.rejected\_rows
|
v
PostgreSQL (sales\_db)
* raw\_data.stg\_sales        (43 clean rows)
* audit.rejected\_rows       (8 bad rows with reasons)
* audit.pipeline\_runs       (run history)
|
v
dbt Models
* analytics.stg\_sales            (staging view)
* analytics.int\_sales\_enriched   (intermediate table, adds categories/tiers)
* analytics.daily\_sales\_metrics  (final mart, daily aggregates)

## 

## Project structure

sales\_pipeline/
docker-compose.yml       <- defines postgres, etl, dbt containers
Dockerfile.python        <- builds the Python ETL container
Dockerfile.dbt           <- builds the dbt container
etl.py                   <- extract, clean, load script
orchestrate.py           <- runs the full pipeline in order
requirements.txt         <- Python dependencies
data/
raw/
sales\_data.csv     <- input data file
dbt/
dbt\_project.yml       <- dbt project config
profiles.yml          <- database connection settings
models/
staging/
stg\_sales.sql         <- staging view
sources.yml           <- declares raw\_data source
schema.yml            <- tests and documentation
intermediate/
int\_sales\_enriched.sql  <- intermediate model
marts/
daily\_sales\_metrics.sql <- final analytical model
logs/                    <- ETL log files

## 

## Prereqs

* Docker Desktop (docker.com/products/docker-desktop)
* Python 3.11 or higher

No other installations needed. Docker handles PostgreSQL and dbt.

## 

## How To run



### Total pipeline

python orchestrate.py



### Step by step

docker compose up -d postgres
docker compose run --rm etl
docker compose run --rm dbt

### 

### dbt tests only

docker compose run --rm dbt dbt test --profiles-dir /app/dbt --project-dir /app/dbt

### 

### Shut it all down

docker compose down

## 

## Query the data

Connect to the database:
docker compose exec postgres psql -U sales\_user -d sales\_db

Useful queries:
SELECT \* FROM raw\_data.stg\_sales LIMIT 10;
SELECT \* FROM audit.rejected\_rows;
SELECT \* FROM analytics.daily\_sales\_metrics ORDER BY sale\_date;
SELECT \* FROM audit.pipeline\_runs;

\\q to exit.

## 

## Data quality

ETL rejects rows that fail any of these rules:

* Date is unparseable
* Price is missing, zero, or non-numeric (e.g. Error, na)
* Quantity is missing or less than 1
* Product name is empty

Rejected rows are saved to audit.rejected\_rows with a rejection\_reason column.

dbt runs 17 tests after every build:

* not\_null checks on key columns
* accepted\_values checks on region, product\_category, price\_tier

## 

## Repeat with new data

Replace data/raw/sales\_data.csv with new file using the same column structure.
Then run: python orchestrate.py

