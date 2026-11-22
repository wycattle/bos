"""feed_functions\\feedcost_basics.py"""

import inspect
from pathlib import Path
import pandas as pd
import numpy as np
from container import get_dependency


class FeedcostBasics:
    print(f"FeedcostBasics instantiated by: {inspect.stack()[1].filename}")


    GROUP_COLS = ['fresh_kg', 'group_a_kg', 'group_b_kg',
                  'group_c_kg', 'dry_kg', 'heifer_kg']
    GROUP_PREFIXES = ['fresh', 'a', 'b', 'c', 'd', 'h']
    GROUP_LABELS = ['F', 'A', 'B', 'C', 'D', 'H']

    def __init__(self):
        print(f"FeedcostBasics instantiated by: {inspect.stack()[1].filename}")

    def load(self):
        self.milk_basics = get_dependency("milk_basics")
        self.date_range  = get_dependency("date_range")
        self.FDL         = get_dependency("feedcost_data_loader")
        self.FDP         = get_dependency("feedcost_data_processor")
        self.process()

    def process(self):
        self.truncated_rng_daily = self.date_range.truncated_date_range_daily

        # Copy necessary data from data processor
        self.basic_feed_types     = self.FDP.basic_feed_types.copy()
        self.daily_amt_feed_types = self.FDP.daily_amt_feed_types.copy()
        self.price_sequence_dict  = self.FDP.price_sequence_dict.copy()
        self.daily_amt_dict       = self.FDP.daily_amt_dict.copy()

        self.feed_types = list(self.price_sequence_dict.keys())

        # Compute cost for each group (six individual DataFrames)
        self._calculate_all_group_costs()

        # Combine into a single daily DataFrame (cost/cow/day per group)
        self.avg_feedcost_by_group_daily = self.create_avg_feedcost_by_group_daily()

    def _calculate_all_group_costs(self):
        """
        Accumulate daily total cost per cow for each group across all feeds.

        Stores the result in six attributes:
            self.feedcost_F_df, self.feedcost_A_df, ... self.feedcost_H_df
        each having a single column named 'totalcost<GROUP>' and index equal
        to self.truncated_rng_daily.
        """
        # Initialize totals to zero for every date
        group_totals = {prefix: pd.Series(0.0, index=self.truncated_rng_daily)
                        for prefix in self.GROUP_PREFIXES}

        for feed in self.feed_types:
            price_series = self._get_daily_price(feed)
            amount_df    = self._get_daily_amounts(feed)

            # For missing group column, skip with a warning
            for col, prefix in zip(self.GROUP_COLS, self.GROUP_PREFIXES):
                if col not in amount_df.columns:
                    print(f"Warning: column '{col}' not found in feed '{feed}' amounts. "
                          f"Skipping this column.")
                    continue

                kg = amount_df[col].reindex(self.truncated_rng_daily).fillna(0.0)
                cost = price_series * kg
                # Add to existing total for that group
                group_totals[prefix] = group_totals[prefix].add(cost, fill_value=0.0)

        # Build individual DataFrames and assign to attributes
        self.feedcost_F_df = pd.DataFrame({'totalcostF': group_totals['fresh']},
                                          index=self.truncated_rng_daily)
        self.feedcost_A_df = pd.DataFrame({'totalcostA': group_totals['a']},
                                          index=self.truncated_rng_daily)
        self.feedcost_B_df = pd.DataFrame({'totalcostB': group_totals['b']},
                                          index=self.truncated_rng_daily)
        self.feedcost_C_df = pd.DataFrame({'totalcostC': group_totals['c']},
                                          index=self.truncated_rng_daily)
        self.feedcost_D_df = pd.DataFrame({'totalcostD': group_totals['d']},
                                          index=self.truncated_rng_daily)
        self.feedcost_H_df = pd.DataFrame({'totalcostH': group_totals['h']},
                                          index=self.truncated_rng_daily)

    def _get_daily_price(self, feed):
        """
        Return a daily price Series for the given feed.

        Zeros are treated as missing and forward‑filled, then any remaining
        missing (leading) are set to 0.
        """
        price_df = self.price_sequence_dict[feed].copy()
        if 'datex' not in price_df.columns:
            raise KeyError(f"Price data for feed '{feed}' must contain a 'datex' column.")

        price_df['datex'] = pd.to_datetime(price_df['datex'])
        price_df = price_df.sort_values('datex').drop_duplicates(subset='datex', keep='last')
        price_series = price_df.set_index('datex')['unit_price']

        # Treat 0 as missing, forward fill, then fill leading NaNs with 0
        daily_price = (price_series
                       .replace(0, np.nan)
                       .ffill()
                       .reindex(self.truncated_rng_daily, method='ffill')
                       .fillna(0.0))
        return daily_price

    def _get_daily_amounts(self, feed):
        """
        The amounts are forward‑filled across the truncated daily range; any
        dates before the first amount record are filled with 0.0.
        """
        amt_df = self.daily_amt_dict[feed].copy()
        if 'datex' in amt_df.columns:
            amt_df['datex'] = pd.to_datetime(amt_df['datex'])
            amt_df = amt_df.sort_values('datex').drop_duplicates(subset='datex', keep='last')
            amt_df = amt_df.set_index('datex')


        numeric_cols = amt_df.select_dtypes(include=[np.number]).columns
        amt_df[numeric_cols] = amt_df[numeric_cols].ffill().fillna(0.0)
        amt_df = amt_df.reindex(self.truncated_rng_daily, method='ffill').fillna(0.0)
        return amt_df

    def create_avg_feedcost_by_group_daily(self):
        """
        Combine the six group cost DataFrames into a single tidy DataFrame.

        Returns
        -------
        pd.DataFrame
            Index: truncated_rng_daily
            Columns: ['F','A','B','C','D','H']
            Values: daily feed cost per cow for that group.
        """
        data = {
            'F': self.feedcost_F_df['totalcostF'],
            'A': self.feedcost_A_df['totalcostA'],
            'B': self.feedcost_B_df['totalcostB'],
            'C': self.feedcost_C_df['totalcostC'],
            'D': self.feedcost_D_df['totalcostD'],
            'H': self.feedcost_H_df['totalcostH'],
        }
        df = pd.DataFrame(data, index=self.truncated_rng_daily)
        # Ensure all dates are present and fill any missing with 0
        df = df.reindex(self.truncated_rng_daily).fillna(0.0)

        self.avg_feedcost_by_group_daily = df
        return self.avg_feedcost_by_group_daily

    def write_to_csv(self):
        output_dir = Path("/home/alanw/Documents/vsCode_output/feed")
        output_dir.mkdir(parents=True, exist_ok=True)
        self.avg_feedcost_by_group_daily.to_csv(output_dir / "avg_feedcost_by_group_daily.csv")




if __name__ == "__main__":
    obj = FeedcostBasics()
    obj.load()
    obj.write_to_csv()

