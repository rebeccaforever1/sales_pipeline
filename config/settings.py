"""
Configuration loading from YAML and environment variables
"""

import os
import yaml
from pathlib import Path
from dataclasses import dataclass


def load_yaml_config(file_path: str) -> dict:
    """Load YAML configuration file"""
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)


@dataclass
class DatabaseConfig:
    """Database configuration from YAML + env vars"""
    
    @staticmethod
    def from_yaml(yaml_config: dict) -> 'DatabaseConfig':
        db_config = yaml_config.get('database', {}).get('connection', {})
        
        return DatabaseConfig(
            host=os.getenv('PG_HOST', db_config.get('host', 'localhost').replace('${PG_HOST:-', '').rstrip('}')),
            port=int(os.getenv('PG_PORT', db_config.get('port', '5432').replace('${PG_PORT:-', '').rstrip('}'))),
            user=os.getenv('PG_USER', db_config.get('user', 'sales_user').replace('${PG_USER:-', '').rstrip('}')),
            password=os.getenv('PG_PASSWORD', db_config.get('password', 'sales_password').replace('${PG_PASSWORD:-', '').rstrip('}')),
            database=os.getenv('PG_DB', db_config.get('database', 'sales_db').replace('${PG_DB:-', '').rstrip('}'))
        )
    
    def __init__(self, host, port, user, password, database):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
    
    @property
    def connection_string(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


# Load configuration
CONFIG_DIR = Path(__file__).parent.parent / 'config'
pipeline_config = load_yaml_config(CONFIG_DIR / 'pipeline.yaml')
config = DatabaseConfig.from_yaml(pipeline_config)