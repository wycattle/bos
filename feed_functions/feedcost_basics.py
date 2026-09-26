"""feed_functions\\feedcost_basics.py"""

import inspect
import pandas as pd
from container import get_dependency


class FeedcostBasics:

    def __init__(self):
        print(f"FeedcostBasics instantiated by: {inspect.stack()[1].filename}")


        self.milk_basics = None
        self.date_range = None
        self.rng_daily = None

        # Canonical active inventory types -- populated in load_and_process
        # from feed_type_feed_invoice_ledger view rather than hardcoded here.
        self.feed_types = None

        self.price_sequence_dict = {}
        self.daily_amt_dict = {}

        # One daily cost DataFrame per group -- each has one column per
        # feed type plus a 'totalcost{X}' sum column.
        self.feedcost_F_df = None
        self.feedcost_A_df = None
        self.feedcost_B_df = None
        self.feedcost_C_df = None
        self.feedcost_D_df = None
        self.feedcost_H_df = None

        self.iu_merge_df = None

    def load(self):
        self.milk_basics= get_dependency("milk_basics")
        self.date_range = get_dependency("date_range")
        self.FDL        = get_dependency("feedcost_data_loader")
        self.FDP        = get_dependency("feedcost_data_processor")
        self.process()
        
    def process(self):
        self.rng_daily  = self.date_range.date_range_daily
        
        self.basic_feed_types       = self.FDP.basic_feed_types.copy() #series
        self.daily_amt_feed_types   = self.FDP.daily_amt_feed_types.copy()
        self.price_sequence_dict    = self.FDP.price_sequence_dict.copy()
        self.daily_amt_dict         = self.FDP.daily_amt_dict.copy()
        
        self.feed_types = list(self.price_sequence_dict.keys())
        
        #methods
        [self.feedcost_F_df, self.feedcost_A_df,
         self.feedcost_B_df, self.feedcost_C_df,
         self.feedcost_D_df, self.feedcost_H_df]                        = self._calculate_all_group_costs()


    # Accumulate daily total cost per group across all feeds
    def _calculate_all_group_costs(self):
        group_cols = ['fresh_kg', 'group_a_kg', 'group_b_kg', 'group_c_kg', 'dry_kg', 'heifer_kg']
        group_prefixes = ['fresh', 'a', 'b', 'c', 'd', 'h']
        group_totals = {prefix: None for prefix in group_prefixes}

        for feed in self.feed_types:
            # --- Align price to daily index ---
            price_df = self.price_sequence_dict[feed].copy()
            # Ensure datex is datetime and set as index
            price_df = price_df.set_index('datex')
            # Reindex to full daily range, forward-fill
            daily_price_series = price_df['unit_price'].reindex(self.rng_daily, method='ffill').fillna(0).values

            # --- Daily amount DataFrame ---
            daily_amt_series = self.daily_amt_dict[feed].copy()
            # Ensure it is indexed by date (assuming datex column or index)
            if 'datex' in daily_amt_series.columns:
                daily_amt_series['datex'] = pd.to_datetime(daily_amt_series['datex'])
                daily_amt_series = daily_amt_series.set_index('datex')
            # Reindex to daily range, fill missing with 0
            daily_amt_series = daily_amt_series.reindex(self.rng_daily, method='ffill').fillna(0)

            for col, prefix in zip(group_cols, group_prefixes):
                kg = daily_amt_series[col].values
                cost = daily_price_series * kg
                if group_totals[prefix] is None:
                    group_totals[prefix] = cost
                else:
                    group_totals[prefix] += cost

        self.feedcost_F_df = pd.DataFrame({'totalcostF': group_totals['fresh']}, index=self.rng_daily)
        self.feedcost_A_df = pd.DataFrame({'totalcostA': group_totals['a']}, index=self.rng_daily)
        self.feedcost_B_df = pd.DataFrame({'totalcostB': group_totals['b']}, index=self.rng_daily)
        self.feedcost_C_df = pd.DataFrame({'totalcostC': group_totals['c']}, index=self.rng_daily)
        self.feedcost_D_df = pd.DataFrame({'totalcostD': group_totals['d']}, index=self.rng_daily)
        self.feedcost_H_df = pd.DataFrame({'totalcostH': group_totals['h']}, index=self.rng_daily)
        
        return self.feedcost_F_df, self.feedcost_A_df, self.feedcost_B_df, self.feedcost_C_df, self.feedcost_D_df, self.feedcost_H_df 
    
if __name__ == "__main__":
    obj = FeedcostBasics()
    obj.load()
