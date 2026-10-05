"""feed_functions\\feedcost_by_group_by_day.py"""

import inspect
import pandas as pd
from pathlib import Path
from container import get_dependency

class FeedCostByGroupByDay:
    def __init__(self):
        print(f"FeedCostByGroupByDay instantiated by: {inspect.stack()[1].filename}")
        
        self.BD = None
        self.DR = None
        self.MG = None
        self.FB = None
        self.WD = None

        
        #methods
        self.wyids = None
        self.dates = None
        self.groups = None
        self.cost_f = None
        self.cost_a = None
        self.cost_b = None
        self.cost_c = None
        self.cost_d = None
        self.cost_h = None
        self.feedfeedcost_by_group_by_day_df = None
        self.feedcost_by_group_by_week_df = None
        
    def load(self):
        self.MB = get_dependency('milk_basics')
        self.DR = get_dependency('date_range')
        self.MG = get_dependency('model_groups')
        self.FB = get_dependency('feedcost_basics')
        self.WD = get_dependency('wet_dry')
        self.process()
        
    def process(self):
        self.wyids  = self.MB.data['bd'].index
        self.dates  = self.DR.date_range_weekly
        self.groups_daily   = self.MG.model_groups_daily
        self.groups_weekly  = self.MG.model_groups_weekly
        self.groups_monthly = self.MG.model_groups_monthly
        
        self.cost_f = self.FB.feedcost_F_df
        self.cost_a = self.FB.feedcost_A_df
        self.cost_b = self.FB.feedcost_B_df
        self.cost_c = self.FB.feedcost_C_df
        self.cost_d = self.FB.feedcost_D_df
        self.cost_h = self.FB.feedcost_H_df

     #methods
        self.feedfeedcost_by_group_by_day_df    = self.create_feedcost_by_group_by_day()
        self.feedcost_by_group_by_week_df   = self.create_feedcost_by_group_by_week()
        
        [self.feedcost_by_group_by_month_by_cow, 
        self.total_feedcost_by_cow]         = self.create_feedcost_by_group_by_month()
        
            
    def create_feedcost_by_group_by_day(self):
        
        groups = self.groups_daily.copy()

        cost_map = {
        'F': self.cost_f,
        'A': self.cost_a,
        'B': self.cost_b,
        'C': self.cost_c,
        'D': self.cost_d,
        'H': self.cost_h,
        }


        # df.stack ---- Returns a reshaped DataFrame or Series having a multi-level index 
        # with one or more new inner-most levels compared to the current DataFrame.
         
        # The new inner-most levels are created by pivoting the columns of the current dataframe:
        # if the columns have a single level, the output is a Series;
        # if the columns have multiple levels, the new index level(s) is (are) taken 
        # from the prescribed level(s) and the output is a DataFrame.
        #.stack() flattens that entire grid into one long column in a single C-level operation

        # long: one row per (wy_id, date) -> group letter
        long = groups.stack(future_stack=True).rename('group').reset_index() #future_stack is for new (future) implementation
        long.columns = [ 'date', 'wy_id',  'group']

        #squeeze each cost frame down to a Series before concat
        cost_series = {}
        for group, df in cost_map.items():
            series = df.iloc[:, 0] if isinstance(df, pd.DataFrame) else df   # totalcostF -> plain Series
            series.index = pd.to_datetime(series.index).normalize()
            cost_series[group] = series


        # build a single date x feed-type cost table, then long-ify it
        cost_wide = pd.concat(cost_series, axis=1)          # columns: F, A, B, C, D (single level)
        cost_long = cost_wide.stack(future_stack=True).rename('cost').reset_index()
        cost_long.columns = ['date', 'group', 'cost']
        
        cost_wide.index = pd.to_datetime(cost_wide.index).normalize()
        cost_long = cost_wide.stack(future_stack=True).rename('cost').reset_index()
        cost_long.columns = ['date', 'group', 'cost']

        merged = long.merge(cost_long, on=['date', 'group'], how='left')



        cost_by_group_df = merged.pivot(index='date', columns='wy_id', values='cost')
        self.feedcost_by_group_by_day_df = cost_by_group_df
        return self.feedcost_by_group_by_day_df
        
        
    def create_feedcost_by_group_by_week(self):
        groups = self.groups_weekly.copy()  # already weekly, W-SUN anchored, from model_groups

        cost_map = {
            'F': self.cost_f,
            'A': self.cost_a,
            'B': self.cost_b,
            'C': self.cost_c,
            'D': self.cost_d,
            'H': self.cost_h,
        }

        # long format: one row per (week, wy_id) -> group letter
        long = groups.stack(future_stack=True).rename('group').reset_index()
        long.columns = ['date', 'wy_id', 'group']

        # squeeze each daily cost frame to a Series, normalize, then resample to
        # weekly totals on the SAME anchor as groups/period_weekly/wet_dry_days_weekly.
        # min_count=1: a week with zero logged days should read NaN, not a false 0.0
        cost_series = {}
        for group, df in cost_map.items():
            series = df.iloc[:, 0] if isinstance(df, pd.DataFrame) else df
            series.index = pd.to_datetime(series.index).normalize()
            cost_series[group] = series.resample('W').sum(min_count=1)

        cost_wide = pd.concat(cost_series, axis=1)  # weekly date x {F,A,B,C,D,H}
        cost_long = cost_wide.stack(future_stack=True).rename('cost').reset_index()
        cost_long.columns = ['date', 'group', 'cost']

        merged = long.merge(cost_long, on=['date', 'group'], how='left')

        # returns weekly feedcost total of each cow (from start date) 

        cost_by_group_by_week_df = merged.pivot(index='date', columns='wy_id', values='cost')
        self.feedcost_by_group_by_week_df = cost_by_group_by_week_df
        return self.feedcost_by_group_by_week_df

            
    def create_feedcost_by_group_by_month(self):
        groups = self.groups_monthly.copy()  # must be MS-anchored monthly group labels, matching monthly_avg

        cost_map = {
            'F': self.cost_f,
            'A': self.cost_a,
            'B': self.cost_b,
            'C': self.cost_c,
            'D': self.cost_d,
            'H': self.cost_h,
        }

        # long format: one row per (month, wy_id) -> group letter
        long = groups.stack(future_stack=True).rename('group').reset_index()
        long.columns = ['date', 'wy_id', 'group']
        long['date'] = pd.to_datetime(long['date']).dt.to_period('M').astype(str)

        # squeeze each daily cost frame to a Series, normalize, then resample to
        # monthly totals on the SAME anchor as groups ('MS' = month-start label).
        # min_count=1: a month with zero logged days should read NaN, not a false 0.0
        cost_series = {}
        for group, df in cost_map.items():
            series = df.iloc[:, 0] if isinstance(df, pd.DataFrame) else df
            series.index = pd.to_datetime(series.index).normalize()
            cost_series[group] = series.resample('MS').sum(min_count=1)

        cost_wide = pd.concat(cost_series, axis=1)  # monthly date x {F,A,B,C,D,H}
        cost_long = cost_wide.stack(future_stack=True).rename('cost').reset_index()
        cost_long.columns = ['date', 'group', 'cost']
        cost_long['date'] = pd.to_datetime(cost_long['date']).dt.to_period('M').astype(str)
        
        merged = long.merge(cost_long, on=['date', 'group'], how='left')

        # returns monthly feedcost total of each cow (from start date) 
        cost_by_group_by_month_df = merged.pivot(index='date', columns='wy_id', values='cost')
        self.feedcost_by_group_by_month_by_cow = cost_by_group_by_month_df
        self.total_feedcost_by_cow = self.feedcost_by_group_by_month_by_cow.sum(axis=0)
        
        return self.feedcost_by_group_by_month_by_cow, self.total_feedcost_by_cow
        
    
    def write_to_csv(self):
        output_dir = Path("/home/alanw/Documents/vsCode_output/feed")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        self.feedcost_by_group_by_day_df.to_csv( output_dir / "feedcost_by_group_by_day_df.csv")
        self.feedcost_by_group_by_month_by_cow.to_csv(output_dir / "feedcost_by_group_by_month_by_cow.csv") 
        self.total_feedcost_by_cow.to_csv(output_dir / "self.total_feedcost_by_cow.csv")  
    
         
if __name__ == "__main__":
    obj = FeedCostByGroupByDay()
    obj.load()
    obj.write_to_csv()