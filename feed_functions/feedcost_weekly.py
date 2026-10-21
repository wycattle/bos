'''feed_functions/feedcost_weekly.py'''
import inspect
from pathlib import Path

import numpy as np
import pandas as pd

from container import get_dependency

GROUPS = ['F', 'A', 'B', 'C', 'D', 'H']   # Fresh, A, B, C, Dry, Heifer
WEEK = 'W'                                 # single weekly anchor; must match
                                           # milk_aggregates / wet_dry / model_groups


class FeedCostWeekly:
    

    def __init__(self):
        print(f"FeedCostWeekly instantiated by: {inspect.stack()[1].filename}")


    def load(self):
        self.FB = get_dependency('feedcost_basics')
        self.MG = get_dependency('model_groups')
        self.SD = get_dependency('status_data')
        self.DR = get_dependency('date_range')
        self.process()

    def process(self):
        
        self.truncated_date_range_weekly = self.DR.truncated_date_range_weekly

        groups_1    = self._int_cols(self.MG.model_groups_weekly)
        self.groups = groups_1.loc[self.truncated_date_range_weekly]

        
        # methods
        # col headers are groups: Fresh, A etc
        self.avg_feedcost_by_group_weekly= self.create_avg_feedcost_by_group_weekly()
        self.days_present                = self.create_days_present()

        #keep in this order
        self.avg_feedcost_by_cow_weekly  = self.create_avg_feedcost_by_cow_weekly()
        self.month_weights               = self.create_month_weights()
        self.avg_feedcost_by_cow_monthly = self.create_avg_feedcost_by_cow_monthly()

        #total for all cows
        self.feedcost_total_weekly  = self.avg_feedcost_by_cow_weekly .sum(axis=1) * 7
        self.feedcost_total_monthly = self.avg_feedcost_by_cow_monthly.sum(axis=1) * 7
        
        [self.missing_cost_grid, 
        self.missing_cost ]         = self.create_missing_cost()






    #NOTE: this needs to be calc before the weekly by cow ()
    def create_avg_feedcost_by_group_weekly(self):
        """Weekly-mean cost for each group."""
        # group by week and compute the mean cost for each group
        cost_series = {
            g: self._as_series(getattr(self.FB, f'feedcost_{g}_df'))
            for g in GROUPS
            }

        # Concatenate the results into a DataFrame
        self.avg_feedcost_by_group_weekly = pd.concat(
            {g: s.resample(WEEK).sum() for g, s in cost_series.items()},axis=1)

        return self.avg_feedcost_by_group_weekly


    def create_days_present(self):
        """Days per week each cow was present on the farm"""
        status = self.SD.status_col_all.loc[self.truncated_date_range_weekly]
        present = (~status.isin(['nby', 'gone'])).resample(WEEK).sum()
        present = self._int_cols(present)
        return present.reindex(index=self.groups.index,
                               columns=self.groups.columns)



    
    def create_avg_feedcost_by_cow_weekly(self):
        """Cost per cow-week: group cost for that week x days present."""
        grp = self.groups
        cost = pd.DataFrame(np.nan, index=grp.index, columns=grp.columns)
        costs = self.avg_feedcost_by_group_weekly.reindex(grp.index)
        
        for g in GROUPS:
            if g in costs.columns:
                # Broadcast group costs to match cost's shape (429 weeks × 321 cows)
                # numpy.tile function constructs a new NumPy array by repeating an input array a specified number of times along each axis.
                group_costs = np.tile(costs[g].values[:, np.newaxis], (1, len(grp.columns)))
                cost = cost.where(grp != g, group_costs)

        # 'days_present' shape and 'cost' shape must be the same
        self.avg_feedcost_by_cow_weekly = cost * self.days_present   
        return self.avg_feedcost_by_cow_weekly

    
   
    def create_avg_feedcost_by_cow_monthly(self):
        
        cost = self.avg_feedcost_by_cow_weekly.fillna(0.0)
        m = self.month_weights.to_numpy() @ cost.to_numpy()
        self.avg_feedcost_by_cow_monthly = pd.DataFrame(m, index=self.month_weights.index, columns=cost.columns)
        return self.avg_feedcost_by_cow_monthly 



    # ---- helpers ----
    def create_missing_cost(self):
        """Flag cow-weeks present but unpriced (e.g. 'G' labels)        """

        grid = self.avg_feedcost_by_cow_weekly.isna() & (self.days_present > 0)
        return grid, grid.sum(axis=1)

    

    def create_month_weights(self):
        """Fraction of each week's 7 calendar days falling in each month.        """
        
        ends = self.avg_feedcost_by_cow_weekly.index.to_numpy()
        days = ends[:, None] - np.arange(6, -1, -1) * np.timedelta64(1, 'D')  # weeks x 7
        months = pd.DatetimeIndex(days.ravel()).to_period('M')
        wk_pos = np.repeat(np.arange(len(ends)), 7)
        weights = (pd.crosstab(months, wk_pos)
               .reindex(columns=range(len(ends)), fill_value=0) / 7)
        weights.index = weights.index.to_timestamp(how='end').normalize()
        assert np.allclose(weights.sum(axis=0), 1), "month_weights columns must sum to 1"
        return weights




    @staticmethod
    def _int_cols(df):
        """Return a copy with cow-id columns cast to int.

        Upstream grids carry float or str ids; mismatched dtypes make
        reindex/where silently return all-NaN, so normalize both sides.
        """
        df = df.copy()
        df.columns = df.columns.astype(float).astype(int)
        return df

    @staticmethod
    def _as_series(x):
        """Squeeze a one-column DataFrame (or Series) to a Series with a
        normalized DatetimeIndex. Works on a copy; the source is untouched."""
        s = (x.iloc[:, 0] if isinstance(x, pd.DataFrame) else x).copy()
        s.index = pd.to_datetime(s.index).normalize()
        return s




    def write_to_csv(self):
        """Dump outputs for inspection. Called from __main__ only."""
        out = Path("/home/alanw/Documents/vsCode_output/feed")
        out.mkdir(parents=True, exist_ok=True)

        self.avg_feedcost_by_group_weekly.to_csv( out / "avg feedcost by group weekly.csv")

        self.avg_feedcost_by_cow_weekly .to_csv(out / "avg_feedcost_by_cow_weekly.csv")
        self.avg_feedcost_by_cow_monthly.to_csv(out / "avg_feedcost_by_cow_monthly.csv")

        self.missing_cost_grid      .to_csv(out / "missing_cost_grid.csv")
        self.missing_cost           .to_csv(out / "missing_cost.csv")


        self.feedcost_total_weekly  .to_csv(out / "feedcost_total_weekly.csv")
        self.feedcost_total_monthly .to_csv(out / "feedcost_total_monthly.csv")


if __name__ == "__main__":
    obj = FeedCostWeekly()
    obj.load()
    obj.write_to_csv()