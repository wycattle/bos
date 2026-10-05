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
    """Weekly feed cost per cow.

    Feed cost depends on the weekly model group, so cost is computed weekly:

        cost[week, cow] = rate[week, group(week, cow)] * days_present[week, cow]

    where ``rate`` is the weekly-mean feed cost per cow-day for that group.
    There is no daily cost grid; the daily group view in ModelGroups is a
    sanity check only.

    Dependencies
    ------------
    feedcost_basics : daily cost per cow-day for each group (feedcost_{g}_df)
    model_groups    : weekly group labels (weeks x cows)
    status_data     : daily status grid, used to count days present per week

    Attributes
    ----------
    rate_weekly : DataFrame, weeks x groups
        Weekly-mean cost per cow-day for each group in GROUPS.
    groups : DataFrame, weeks x cows
        Weekly group labels (H, D, G, F, A, B, C), integer cow columns.
    days_present : DataFrame, weeks x cows
        Days in the week the cow was neither 'nby' nor 'gone'.
    feedcost_weekly : DataFrame, weeks x cows
        Feed cost per cow-week. NaN where the label has no rate (e.g. 'G').
    feedcost_weekly_total : Series, indexed by week
        Herd total per week.
    unpriced : Series, indexed by week
        Count of cows present that week with no cost. Should be 0 whenever
        feed rates exist; non-zero flags 'G' labels or weeks missing rates.
    """

    def __init__(self):
        print(f"FeedCostWeekly instantiated by: {inspect.stack()[1].filename}")
        # load
        self.FB = None
        self.MG = None
        self.SD = None
        # process
        self.rate_weekly = None
        self.groups = None
        self.days_present = None
        # methods
        self.feedcost_weekly = None
        self.feedcost_weekly_total = None
        self.unpriced = None

    def load(self):
        """Fetch dependencies from the container, then run process()."""
        self.FB = get_dependency('feedcost_basics')
        self.MG = get_dependency('model_groups')
        self.SD = get_dependency('status_data')
        self.process()

    def process(self):
        """Build rates, labels, days present, then cost and diagnostics."""
        self.rate_weekly = self.create_rate_weekly()
        self.groups = self._int_cols(self.MG.model_groups_weekly)
        self.days_present = self.create_days_present()
        self.feedcost_weekly = self.create_feedcost_weekly()
        self.feedcost_weekly_total = self.feedcost_weekly.sum(axis=1)
        self.unpriced = self.create_unpriced()

    # ---- helpers ----
    @staticmethod    #A static method does not receive an implicit first argumen
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

    # ---- methods ----
    def create_rate_weekly(self):
        """Weekly-mean cost per cow-day for each group.

        Returns
        -------
        DataFrame, weeks x GROUPS, on the WEEK anchor.
        """
        rate = pd.concat(
            {g: self._as_series(getattr(self.FB, f'feedcost_{g}_df'))
             for g in GROUPS},
            axis=1)
        return rate.resample(WEEK).mean()

    def create_days_present(self):
        """Days per week each cow was present on the farm.

        Present = daily status not in {'nby', 'gone'}. Handles partial first
        and last weeks and cows that die or arrive mid-week.

        Returns
        -------
        DataFrame, weeks x cows, aligned to ``self.groups``.
        """
        status = self.SD.status_col_all
        present = (~status.isin(['nby', 'gone'])).resample(WEEK).sum()
        present = self._int_cols(present)
        return present.reindex(index=self.groups.index,
                columns=self.groups.columns)

    def create_feedcost_weekly(self):
        """Cost per cow-week: group rate for that week x days present.

        Labels without a rate (e.g. 'G' missing) stay NaN so gaps are
        visible rather than silently zero.

        Returns
        -------
        DataFrame, weeks x cows.
        """
        grp = self.groups
        rate = self.rate_weekly.reindex(grp.index)
        cost = pd.DataFrame(np.nan, index=grp.index, columns=grp.columns)
        for g in GROUPS:
            r = np.broadcast_to(rate[g].to_numpy()[:, None], cost.shape)
            cost = cost.where(grp != g, r)
        return cost * self.days_present

    def create_unpriced(self):
        """Per week, number of cows present but with no cost (data-quality
        check; see class docstring)."""
        miss = self.feedcost_weekly.isna() & (self.days_present > 0)
        return miss.sum(axis=1)

    def write_to_csv(self):
        """Dump outputs for inspection. Called from __main__ only."""
        out = Path("/home/alanw/Documents/vsCode_output/feed")
        out.mkdir(parents=True, exist_ok=True)
        
        self.rate_weekly            .to_csv(out / "rate_weekly.csv")
        self.feedcost_weekly        .to_csv(out / "feedcost_weekly.csv")
        self.feedcost_weekly_total  .to_csv(out / "feedcost_weekly_total.csv")
        self.unpriced               .to_csv(out / "unpriced.csv")


if __name__ == "__main__":
    obj = FeedCostWeekly()
    obj.load()
    obj.write_to_csv()