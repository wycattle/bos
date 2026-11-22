'''feed_functions/feedcost_data.py'''
import inspect
from pathlib import Path

import numpy as np
import pandas as pd

from container import get_dependency

GROUPS         = ['F', 'A', 'B', 'C', 'D', 'H']   # Fresh, A, B, C, Dry, Heifer
MILKING_GROUPS = ['F', 'A', 'B', 'C']
WEEK           = 'W'                               # must match milk_aggregates / wet_dry / model_groups
CARRY_DAYS     = 7                                 # max days a prior milking label may be carried forward


class FeedCostData:

    def __init__(self):
        print(f"FeedCostData instantiated by: {inspect.stack()[1].filename}")

    def load(self):
        self.FB = get_dependency('feedcost_basics')
        self.MG = get_dependency('model_groups')
        self.SD = get_dependency('status_data')
        self.WD = get_dependency('wet_dry')
        self.DR = get_dependency('date_range')
        self.process()

    def process(self):
        self.truncated_date_range_weekly = self.DR.truncated_date_range_weekly
        self.truncated_date_range_daily  = self.DR.truncated_date_range_daily

        # Daily group cost (cost/cow/day for each group) comes from FeedcostBasics
        self.avg_feedcost_by_group_daily = self.FB.avg_feedcost_by_group_daily.reindex(
            self.truncated_date_range_daily
        ).fillna(0.0)

        # Weekly model_groups labels (full range), cow ids as int
        self.groups = self._int_cols(self.MG.model_groups_weekly)

        # Daily: assign each cow-day to a feed group, cost it, then resample to weekly
        self.group_assigned_daily    = self.create_group_assigned_daily()
        [self.daily_feed_cost_per_cow, 
         self.cumulative_avg_feedcost_by_cow_daily] = self.create_avg_feedcost_by_cow_daily()

        self.avg_feedcost_by_group_weekly           = self.create_avg_feedcost_by_group_weekly()

        [self.avg_feedcost_by_cow_weekly,
         self.cumulative_avg_feedcost_by_cow_weekly] = self.create_avg_feedcost_by_cow_weekly()

        self.month_weights               = self.create_month_weights()
        self.avg_feedcost_by_cow_monthly = self.create_avg_feedcost_by_cow_monthly()

        self.feedcost_total_weekly  = self.avg_feedcost_by_cow_weekly.sum(axis=1)
        self.feedcost_total_monthly = self.avg_feedcost_by_cow_monthly.sum(axis=1)

        [self.missing_cost_grid,
         self.missing_cost] = self.create_missing_cost()

    # ---------------------------------------------------------------------
    # Daily group assignment (status + wet_dry + model_groups)
    # ---------------------------------------------------------------------
    def create_group_assigned_daily(self):
        """
        Feed group per cow-day:
          gone / nby                -> None (no cost)
          alive & wet_dry 'H'       -> 'H'
          alive & wet_dry 'D'       -> 'D'
          alive & wet_dry 'W'       -> F/A/B/C from model_groups
        Anything alive that cannot be assigned stays None and is flagged
        in create_missing_cost().
        """
        idx = self.truncated_date_range_daily

        # 1. Alive mask from status (missing status -> absent)
        status = self.SD.status_col_all.reindex(idx).fillna('gone')
        cows   = status.columns
        self.alive_daily = ~status.isin(['gone', 'nby'])

        # 2. Period letter per cow-day from wet_dry: 'H', 'W', 'D', 'gone', NaN
        letter = self.WD.wd_letters_daily.reindex(index=idx, columns=cows)

        # 3. Weekly milking label -> daily. A week-ending label applies to the
        #    7 days ending on it (backfill); trailing partial week uses last label.
        wk  = self.groups.reindex(columns=cows)
        pos = np.minimum(wk.index.searchsorted(idx), len(wk) - 1)
        mg  = pd.DataFrame(wk.to_numpy()[pos], index=idx, columns=cows)
        mg  = mg.where(mg.isin(MILKING_GROUPS))      # keep F/A/B/C only
        mg  = mg.ffill(limit=CARRY_DAYS)             # dry-off / 'G' weeks: carry last milking label

        # 4. Combine
        alive = self.alive_daily
        h = (alive & letter.eq('H')).to_numpy()
        d = (alive & letter.eq('D')).to_numpy()
        w = (alive & letter.eq('W')).to_numpy() & mg.notna().to_numpy()

        out = np.select([h, d, w], ['H', 'D', mg.to_numpy()], default=None)
        self.group_assigned_daily = pd.DataFrame(out, index=idx, columns=cows, dtype=object)
        return self.group_assigned_daily

    # ---------------------------------------------------------------------
    # Daily per-cow feed cost
    # ---------------------------------------------------------------------
    def create_avg_feedcost_by_cow_daily(self):
        """Daily cost per cow = daily cost of her assigned group (0 if none)."""
        idx  = self.truncated_date_range_daily
        cost = pd.DataFrame(0.0, index=idx, columns=self.group_assigned_daily.columns)

        for g in GROUPS:
            if g in self.avg_feedcost_by_group_daily.columns:
                indicator = (self.group_assigned_daily == g).astype(float)
                cost += indicator.mul(self.avg_feedcost_by_group_daily[g], axis=0)

        self.daily_feed_cost_per_cow = cost
        self.cumulative_avg_feedcost_by_cow_daily = cost.cumsum()
        return self.daily_feed_cost_per_cow, self.cumulative_avg_feedcost_by_cow_daily

    # ---------------------------------------------------------------------
    # Weekly / monthly aggregations
    # ---------------------------------------------------------------------
    def create_avg_feedcost_by_group_weekly(self):
        """Weekly total cost per group (cost/cow/week)."""
        weekly = self.avg_feedcost_by_group_daily.resample(WEEK).sum()
        weekly = weekly.reindex(self.truncated_date_range_weekly)
        self.avg_feedcost_by_group_weekly = weekly
        return weekly

    def create_avg_feedcost_by_cow_weekly(self):
        """Weekly feed cost per cow = sum of daily feed cost per cow over each week."""
        weekly = self.daily_feed_cost_per_cow.resample(WEEK).sum()
        weekly = weekly.reindex(self.truncated_date_range_weekly)

        self.avg_feedcost_by_cow_weekly = weekly
        self.cumulative_avg_feedcost_by_cow_weekly = weekly.cumsum()
        return self.avg_feedcost_by_cow_weekly, self.cumulative_avg_feedcost_by_cow_weekly

    def create_avg_feedcost_by_cow_monthly(self):
        """Monthly feed cost per cow using week-to-month weights."""
        cost = self.avg_feedcost_by_cow_weekly.fillna(0.0)
        m = self.month_weights.to_numpy() @ cost.to_numpy()
        self.avg_feedcost_by_cow_monthly = pd.DataFrame(
            m, index=self.month_weights.index, columns=cost.columns
        )
        return self.avg_feedcost_by_cow_monthly

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------
    def create_missing_cost(self):
        """
        Flag cow-days where the cow is alive (status not gone/nby) but no feed
        group could be assigned. Weekly grid = any such day in the week;
        missing_cost = number of cows flagged per week.
        """
        self.missing_cost_grid_daily = self.alive_daily & self.group_assigned_daily.isna()

        weekly = self.missing_cost_grid_daily.resample(WEEK).sum()
        grid = (weekly.reindex(self.truncated_date_range_weekly).fillna(0) > 0)
        return grid, grid.sum(axis=1)

    def create_month_weights(self):
        """Fraction of each week's 7 calendar days falling in each month."""
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
        """Return a copy with cow-id columns cast to int."""
        df = df.copy()
        df.columns = df.columns.astype(float).astype(int)
        return df

    @staticmethod
    def _as_series(x):
        """Squeeze a one-column DataFrame (or Series) to a Series with a
        normalized DatetimeIndex."""
        s = (x.iloc[:, 0] if isinstance(x, pd.DataFrame) else x).copy()
        s.index = pd.to_datetime(s.index).normalize()
        return s

    def write_to_csv(self):
        """Dump outputs for inspection. Called from __main__ only."""
        out = Path("/home/alanw/Documents/vsCode_output/feed")
        out.mkdir(parents=True, exist_ok=True)

        self.avg_feedcost_by_group_daily.to_csv(out / "avg feedcost by group daily.csv")
        self.avg_feedcost_by_group_weekly.to_csv(out / "avg feedcost by group weekly.csv")
        self.group_assigned_daily.to_csv(out / "group_assigned_daily.csv")
        self.daily_feed_cost_per_cow.to_csv(out / "daily_feed_cost_per_cow.csv")
        self.avg_feedcost_by_cow_weekly.to_csv(out / "avg_feedcost_by_cow_weekly.csv")
        self.avg_feedcost_by_cow_monthly.to_csv(out / "avg_feedcost_by_cow_monthly.csv")
        self.missing_cost_grid_daily.to_csv(out / "missing_cost_grid_daily.csv")
        self.missing_cost_grid.to_csv(out / "missing_cost_grid.csv")
        self.missing_cost.to_csv(out / "missing_cost.csv")
        self.feedcost_total_weekly.to_csv(out / "feedcost_total_weekly.csv")
        self.feedcost_total_monthly.to_csv(out / "feedcost_total_monthly.csv")
        self.cumulative_avg_feedcost_by_cow_weekly.to_csv(
            out / "cumulative_avg_feedcost_by_cow_weekly.csv"
        )
        self.cumulative_avg_feedcost_by_cow_daily.to_csv(
            out / "cumulative_avg_feedcost_by_cow_daily.csv"
        )
                


if __name__ == "__main__":
    obj = FeedCostData()
    obj.load()
    obj.write_to_csv()
    from container import get_dependency
    SD = get_dependency("status_data")
    print(obj.SD.status_col_all.loc['2023-06-19':'2023-06-27', 15])
    print(obj.group_assigned_daily.loc['2023-06-19':'2023-06-27', 15])
    fb = obj.FB
    for feed in fb.feed_types:
        p = fb.price_sequence_dict[feed]
        a = fb.daily_amt_dict[feed]
        print(feed,
            "| first price:", pd.to_datetime(p['datex']).min().date(),
            "| first amount:", pd.to_datetime(a['datex'] if 'datex' in a.columns else a.index).min().date())
        
