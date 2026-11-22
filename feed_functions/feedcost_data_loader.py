
import pandas as pd
from   pipeline.neon.neon_connect import get_engine, read_sql_table_traced
# from container import get_dependency


class FeedCostDataLoader:
    """Handles raw extraction from Neon Postgres – no processing."""
    def __init__(self):
        self.engine = get_engine()
        
    def load_basic_feed_types(self):
        with self.engine.connect() as conn:
            return read_sql_table_traced('feed_daily_amt_last_rows', conn)

        
    #this is a list of the feed types in the daily amt ledger
    def load_feed_type_feed_daily_amt_ledger(self):
        with self.engine.connect() as conn:
            return read_sql_table_traced('feed_type_feed_daily_amt_ledger', conn)

    #this is a list of the feed types in the feed_invoice_ledger
    def load_feed_type_feed_invoice_ledger(self):
        with self.engine.connect() as conn:
            return read_sql_table_traced('feed_type_feed_invoice_ledger', conn)

    def load_feed_invoice_ledger(self) -> pd.DataFrame:
        with self.engine.connect() as conn:
            return read_sql_table_traced('feed_invoice_ledger', conn)
        

    def load_feed_daily_amt_ledger(self) -> pd.DataFrame:
        with self.engine.connect() as conn:
            return read_sql_table_traced('feed_daily_amt_ledger', conn)
        
        
    def get_iu_merge(self) -> pd.DataFrame:
        with self.engine.connect() as conn:
            return read_sql_table_traced('iu_merge_formatted', conn)
    
    
class FeedCostDataProcessor:
    """Handles cleaning, type coercion, indexing of raw feed data."""

    def __init__(self, loader: FeedCostDataLoader):
        self.loader = loader
        self.basic_feed_types       = self.process_basic_feed_types()
        self.daily_amt_feed_types   = self.process_daily_amt_feed_types()
        self.price_sequence_dict    = self.process_invoice_ledger()
        self.daily_amt_dict         = self.process_daily_amt_ledger()
        self.iu_merge               = self.process_iu_merge()
        
    def process_basic_feed_types(self) -> pd.DataFrame:
        df = self.loader.load_feed_type_feed_daily_amt_ledger()
        self.basic_feed_types = df
        return self.basic_feed_types
    
    def process_daily_amt_feed_types(self) -> pd.DataFrame:
        df = self.loader.load_feed_daily_amt_ledger()
        #no need to delete cols or rename
        self.daily_amt_feed_types = df
        return self.daily_amt_feed_types

    def process_invoice_ledger(self) -> dict[str, pd.DataFrame]:
        df1 = self.loader.load_feed_invoice_ledger()
        df2 = df1.loc[:, ['payment_date', 'feed_type', 'price_per_kg']].copy()
        df3 = df2.rename(columns={'payment_date' : 'datex', 'price_per_kg' : 'unit_price'})
        
        suffix = '_invoice_detail'
        self.price_sequence_dict = {}
        for feed_type, subset in df3.groupby('feed_type'):
            plain_feed = feed_type.replace(suffix, '') if feed_type.endswith(suffix) else feed_type
            self.price_sequence_dict[plain_feed] = subset.drop(columns='feed_type')
        return self.price_sequence_dict


    def process_daily_amt_ledger(self) -> dict[str, pd.DataFrame]:
        df = self.loader.load_feed_daily_amt_ledger()
        suffix = '_daily_amt'
        self.daily_amt_dict = {}
        for feed_type, subset in df.groupby('feed_type'):
            plain_feed = feed_type.replace(suffix, '') if feed_type.endswith(suffix) else feed_type
            self.daily_amt_dict[plain_feed] = subset.drop(columns='feed_type')
        return self.daily_amt_dict


    def process_iu_merge(self) -> pd.DataFrame:
        df = self.loader.get_iu_merge()
        self.iu_merge = df
        return self.iu_merge

   

if __name__ == "__main__":
    loader = FeedCostDataLoader()
    processor = FeedCostDataProcessor(loader)
    L = FeedCostDataLoader().load_feed_invoice_ledger()
    print(L[L.feed_type.str.startswith('corn')][['payment_date','price_per_kg']])
