'''pipeline/neon/neon_writer2.py'''
import os
from typing import Dict
import pandas as pd
from sqlalchemy import create_engine, Engine
from container import get_dependency

# Database connection
NEON_URL = os.environ.get("NEON_DATABASE_URL")
engine: Engine = create_engine(NEON_URL)

# Registry: module -> table name mapping
DF_REGISTRY: Dict[str, str] = {
    "users": "users",
    "transactions": "transactions",
    "analytics": "daily_aggregates"
}

def write_df_to_neon(df: pd.DataFrame, table: str, if_exists: str = "replace"):
    """Write a DataFrame to a Neon PostgreSQL table."""
    with engine.connect() as conn:
        df.to_sql(table, con=conn, if_exists=if_exists, index=False)

def write_all_to_neon():
    """Fetch DataFrames from the dependency container and write to Neon."""
    container: DependencyContainer = get_dependency()

    for module_name, table_name in DF_REGISTRY.items():
        df: pd.DataFrame = getattr(container, module_name).get_dataframe()  # adjust to your actual API
        write_df_to_neon(df, table_name)

if __name__ == "__main__":
    write_all_to_neon()