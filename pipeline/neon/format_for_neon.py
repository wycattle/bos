import re
import pandas as pd
from sqlalchemy import text


class FormatForNeon:
    """
    Generic Modal-side type coercion + safe write for a DataFrame going to Neon.

    Two ways to type columns:
    - `schema`: {column_name: kind} for columns with stable, known names
      (kind in 'int' | 'float' | 'date' | 'text' | 'bool')
    - `positional_rules`: [(start_idx, end_idx, kind), ...] for columns
      whose *names* change per run (e.g. tenday's rolling
      10-day date columns) but whose *position* is fixed.
      Applied by df.columns[start_idx:end_idx], not by name.
      Use end_idx=None for an open-ended run (e.g. ipiv_pivot_table's
      variable number of lact_num columns) — matches from start_idx
      to however many columns actually exist that run.

    Only handles type fidelity (dtype + real None for missing).
    Display formatting stays in bos_dashboard.
    """

    _PG_TYPE_MAP = {
        "integer": "int"    , "bigint": "int"       , "smallint": "int",
        "text": "text"      , "varchar": "text"     , "char": "text",
        "date": "date"      , "timestamp": "date"   , "boolean": "bool",
        "timestamptz": "date", 
        "double precision": "float" , "real": "float",
        "numeric": "float"          , "float": "float", 
        
    }

    def __init__(self, schema: dict = None, 
                 positional_rules: list = None,  
                 sort_by: list = None):
        self.spec = {}
        for col, pg_type in (schema or {}).items():
            self.spec[col] = self._normalize_kind(pg_type)
        self.positional_rules = positional_rules or []
        # sort_by: list of (column, direction) tuples, applied left-to-right.
        self.sort_by = sort_by or []

    def _sort(self, df: pd.DataFrame) -> pd.DataFrame:
        if not self.sort_by:
            return df
        cols = [c for c, _ in self.sort_by]
        asc  = [d.lower() != "desc" for _, d in self.sort_by]
        return df.sort_values(cols, ascending=asc, kind="stable").reset_index(drop=True)

    # NOTE: apply() and apply_indexed_date() must each be defined EXACTLY
    # ONCE in this class. A Python class body executes top-to-bottom, so a
    # second `def apply(...)` anywhere below silently overwrites the first
    # in the class namespace — no error, no warning, the first definition
    # (and its call to self._sort()) just becomes permanently unreachable.
    # This has already happened twice in this file's history (both methods,
    # independently) and cost real debugging time each time because nothing
    # *fails* — sort_by is silently ignored instead. If you're tempted to
    # add a variant of either method, rename it (e.g. apply_v2) rather than
    # redefining apply/apply_indexed_date, or the same bug recurs.
    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        if out.index.name in self.spec and out.index.name not in out.columns:
            out = out.reset_index()   # e.g. index named 'datex'
        for idx, col in enumerate(out.columns):
            kind = self.spec.get(col) or self._kind_for_positional(idx)
            out[col] = self._coerce_column(out[col], kind)
        return self._sort(out)

    def apply_indexed_date(self, df: pd.DataFrame, index_name: str = "date") -> pd.DataFrame:
        out = df.copy()
        out.index = pd.to_datetime(out.index, errors="coerce")
        out.index.name = index_name
        out = out.reset_index()
        for idx, col in enumerate(out.columns):
            if col == index_name:
                continue
            kind = self.spec.get(col) or self._kind_for_positional(idx)
            out[col] = self._coerce_column(out[col], kind)
        return self._sort(out)

    def _normalize_kind(self, pg_type: str) -> str:
        key = pg_type.strip().lower()
        key = re.sub(r"\s+primary key$", "", key)
        key = re.sub(r"\s+not null$", "", key)
        if key in {"int", "float", "date", "text", "bool"}:
            return key
        return self._PG_TYPE_MAP.get(key, None)

    @classmethod
    def from_ddl_block(cls, ddl_text: str, positional_rules: list = None):
        schema = {}
        for line in ddl_text.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            parts = re.split(r"[\s,|]+", line, maxsplit=1)
            if len(parts) == 2:
                schema[parts[0]] = parts[1]
        return cls(schema=schema, positional_rules=positional_rules)

    @classmethod
    def from_information_schema(cls, table_name: str, engine, positional_rules: list = None):
        with engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = :t ORDER BY ordinal_position"
            ), {"t": table_name}).fetchall()
        schema = {r[0]: r[1] for r in rows}
        return cls(schema=schema, positional_rules=positional_rules)

    def _kind_for_positional(self, col_idx: int):              #to handle cols in the ipiv_pivot_table
        for start, end, kind in self.positional_rules:
            if start <= col_idx and (end is None or col_idx < end):
                return kind
        return None

    def _coerce_column(self, series: pd.Series, kind: str) -> pd.Series:
        if kind == "date":
            if isinstance(series.dtype, pd.PeriodDtype):
                series = series.dt.to_timestamp()
            elif series.dtype == object:
                series = series.map(
                    lambda v: v.to_timestamp() if isinstance(v, pd.Period) else v)
            return pd.to_datetime(series, errors="coerce")
        elif kind == "int":
            return pd.to_numeric(series, errors="coerce").round(0).astype("Int64")
        elif kind == "float":
            return pd.to_numeric(series, errors="coerce")
        elif kind == "bool":
            return series.astype("boolean")
        elif kind == "text":
            out = series.astype(str)
            return out.replace(["nan", "NaN", "None", "<NA>"], None)
        else:
            if not pd.api.types.is_numeric_dtype(series):
                return series.where(series.notna(), None)
            return series

    def _pk_clause(self, pk_col):
        if isinstance(pk_col, (list, tuple)):
            return ", ".join(f'"{c}"' for c in pk_col)
        return f'"{pk_col}"'

    def write(self, df: pd.DataFrame, table_name: str, engine, pk_col=None,
              indexed_date: bool = False, date_index_name: str = "date"):
        typed = (self.apply_indexed_date(df, date_index_name)
                 if indexed_date else self.apply(df))

        with engine.begin() as conn:
            typed.to_sql(table_name, conn, if_exists='replace', index=False)
            print(f"[neon] {table_name} written: {typed.shape}")

            if pk_col:
                conn.execute(text(
                    f'ALTER TABLE "{table_name}" ADD PRIMARY KEY ({self._pk_clause(pk_col)})'
                ))

        return typed

    def write_conn(self, df: pd.DataFrame, table_name: str, conn, pk_col=None,
                   indexed_date: bool = False, date_index_name: str = "date"):
        typed = (self.apply_indexed_date(df, date_index_name)
                 if indexed_date else self.apply(df))

        typed.to_sql(table_name, conn, if_exists='replace', index=False)
        print(f"[neon] {table_name} written: {typed.shape}")

        if pk_col:
            conn.execute(text(
                f'ALTER TABLE "{table_name}" ADD PRIMARY KEY ({self._pk_clause(pk_col)})'
            ))

        return typed