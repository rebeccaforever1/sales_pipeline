# Sales Data Pipeline - Implementation

## Overview
Data pipeline to read CSV containing messy sales data, load to PostgreSQL, and transform via dBT.



## Architecture

		sales_pipeline/
		├── docker-compose.yml
		├── Dockerfile.python
		├── Dockerfile.dbt
		├── requirements.txt
		├── .env.example
		├── .gitignore
		├── Makefile
		├── README.md
		├── config/
		│   ├── __init__.py
		│   ├── settings.py
		│   └── product_catalog.py
		├── src/
		│   ├── __init__.py
		│   ├── main.py
		│   ├── generators/
		│   │   ├── __init__.py
		│   │   ├── base_generator.py
		│   │   └── sales_generator.py
		│   ├── validators/
		│   │   ├── __init__.py
		│   │   ├── base_validator.py
		│   │   └── sales_validator.py
		│   ├── loaders/
		│   │   ├── __init__.py
		│   │   ├── base_loader.py
		│   │   └── postgres_loader.py
		│   └── orchestration/
		│       ├── __init__.py
		│       ├── pipeline.py
		│       └── commands.py
		├── tests/
		│   ├── __init__.py
		│   ├── test_generator.py
		│   ├── test_validator.py
		│   └── test_pipeline.py
		└── dbt/
		    ├── profiles.yml
		    ├── dbt_project.yml
		    ├── sources.yml
		    └── models/
		        ├── staging/
		        │   └── stg_sales.sql
		        └── marts/
		            └── daily_sales_metrics.sql

   
## Quick Start

### Prerequisites
- Docker Desktop
- Python 3.11+

### Setup & Run
```bash
# Clone and enter directory
cd sales_pipeline

# Start services
docker-compose up -d postgres

# Run full pipeline
bash run.sh
