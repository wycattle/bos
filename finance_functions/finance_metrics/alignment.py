'''finance_functions/finance_metrics/alignment.py'''
import  inspect
import  pandas as pd
from    pathlib import Path
from    datetime import datetime, date
from    container import get_dependency
# from    pipeline.neon.neon_connect import get_engine, read_sql_table_traced

from feed_functions.feedcost_basics import FeedcostBasics


class Alignment:
    def __init__(self, feedcost_basics=None):
        print(f"Alignment instantiated by: {inspect.stack()[1].filename}")
    

    def load(self):
        self.SD = get_dependency('status_data')
        self.FCD= get_dependency('feedcost_data')
        self.MB = get_dependency('milk_basics')
        self.WD = get_dependency('wet_dry')
        self.MG = get_dependency('model_groups')

        self.process()

    def process(self):
        self._prepare_data()
        self.col_df = self.create_dataframe()



    def _prepare_data(self):

        date = pd.Timestamp('2023-01-01')

        self.status_col_all = self.SD.status_col_all.loc[date:].copy()
        self.daily_feed_cost_per_cow = self.FCD.daily_feed_cost_per_cow.copy()
        self.avg_feedcost_by_group_daily = self.FCD.avg_feedcost_by_group_daily.loc[date:].copy()

        milk_df     = self.MB.data['milk']
        self.milk   = milk_df.loc[milk_df.index >= date].copy()

        self.period_daily       = self.WD.period_daily.copy()
        self.wd_letters_daily   = self.WD.wd_letters_daily.copy()
        self.wd_lact_num_daily  = self.WD.wd_lact_num_daily.copy()

        model_groups_daily  = self.MG.model_groups_daily.copy()
        self.mgd            = model_groups_daily.loc[date :,:].reindex(self.period_daily.index).ffill()


    def create_dataframe(self):
        """Create a DataFrame from one column of each prepared data source."""

        sources = {
            'status_col_all': self.status_col_all,
            'daily_feed_cost_per_cow': self.daily_feed_cost_per_cow,
            'milk': self.milk,
            'period_daily': self.period_daily,
            'wd_letters_daily': self.wd_letters_daily,
            'wd_lact_num_daily': self.wd_lact_num_daily,
        }


        cow = 94
        # Extract the column if it exists; skip otherwise
        col_dict = {}
        for name, df in sources.items():
            if cow in df.columns:
                col_dict[name] = df[cow]

        # Create the DataFrame (indices will be combined; NaN for missing values)
        self.col_df = pd.DataFrame(col_dict)


        mgd_cow = self.mgd.loc[:,cow]

            # Add group feed-cost columns, aligned by date
        self.col_df = pd.concat(
            [self.col_df, mgd_cow, self.avg_feedcost_by_group_daily],axis=1)
        return self.col_df


if __name__ ==  "__main__":
    obj=Alignment()
    obj.load()
