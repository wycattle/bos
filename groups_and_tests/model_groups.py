'''milk_functions\\model_groups.py'''
import inspect
import pandas as pd
import numpy as np
from pathlib import Path
from container import get_dependency

class ModelGroups:

    def __init__(self):

        print(f"ModelGroups instantiated by: {inspect.stack()[1].filename}")

        self.SD = None
        self.WD = None
        self.IUB = None
        self.IUD = None
        self.MB = None
        self.DR = None
        self.DRM= None
        self.MA = None
        self.IP = None
        self.BSO = None
        
        #process
        self.startdate = None
        self.lastday  = None
        self.fullday = None
        self.wet_dry_days_weekly = None
        self.wet_period_weekly = None

        self.ultra_4 = None
        self.ultra_pivot = None
        self.weeknums = None
        self.liters = None
        self.period = None
        
        self.start_lact = None
        self.stop_lact = None
        self.pregnant = None
        
        self.model_groups_daily = None
        self.model_groups_weekly = None
        self.model_groups_monthly = None
        
        self.model_groups_daily_dict = None
        self.model_groups_weekly_dict = None
        self.model_groups_monthly_dict = None

    def load(self):

        self.SD = get_dependency('status_data')
        self.WD = get_dependency('wet_dry')
        self.wet_dry_days_weekly = self.WD.wet_dry_days_weekly
        self.period_weekly = self.WD.period_weekly
        
        self.IUD= get_dependency('insem_ultra_data')
        self.MB = get_dependency('milk_basics')
        self.DR = get_dependency('date_range')        
        self.MA = get_dependency('milk_aggregates')
        self.IP = get_dependency('is_pregnant')
        self.process()
        
    def process(self):
        
        self.startdate = self.DR.startdate
        self.lastday  = self.MB.lastday
        
        self.fullday    = self.MA.weekly_avg  # created with start date from date_range

        self.weeknums = self.wet_dry_days_weekly  
        
        
        self.liters  = self.fullday      
        self.period  = self.period_weekly    
        
        start_lact_1 = self.MB.data['start_pivot']
        
        ''' #cols are lact nums, rows are wy '''
        self.start_lact = start_lact_1
        
        stop_lact_1  = self.MB.data['stop_pivot']
        self.stop_lact  = stop_lact_1
        
        self.pregnant = self.IP.preg_df_weekly
        
              
        #methods
  
        self.model_groups_daily,
        self.model_groups_daily_dict    = self.create_model_groups_daily()
        
        self.model_groups_weekly,
        self.model_groups_weekly_dict   = self.create_model_groups_weekly()
        
        self.model_groups_monthly,
        self.model_groups_monthly_dict  = self.create_model_groups_monthly()
        
        self.write_to_csv()        
    
       
    def create_model_groups_daily(self):
        liters_1   = self.liters
        week_num_1 = self.weeknums
        pregnant_1 = self.pregnant
        period_1   = self.period
        
        
        # Align all frames to liters_1 so np.select gets same-shape conditions
        week_num_1 = week_num_1 .reindex(index=liters_1.index, columns=liters_1.columns)
        pregnant_1 = pregnant_1 .reindex(index=liters_1.index, columns=liters_1.columns)
        period_1   = period_1   .reindex(index=liters_1.index, columns=liters_1.columns)

        period_letter = period_1.astype('string').apply(
            lambda col: col.str.extract(r'([A-Za-z]+)')[0]
        )
        is_heifer = period_letter == 'H'
        is_dry    = period_letter == 'D'
        is_preg   = pregnant_1 == 'preg'
        missing   = (week_num_1.isna() | liters_1.isna()) & ~is_heifer & ~is_dry

        conditions = [
            is_heifer,
            is_dry,
            missing,
            week_num_1 < 3,
            (week_num_1 >= 3) & (liters_1 >= 15),
            (week_num_1 >= 3) & (liters_1 > 0) & (liters_1 < 15) & is_preg,
            (week_num_1 >= 3) & (liters_1 > 0) & (liters_1 < 15) & ~is_preg,
        ]
        choices = ['H', 'D', None, 'F', 'A', 'C', 'B']

        cond_arrs = [
            c.to_numpy(dtype=bool, na_value=False) if not c.empty
            else np.zeros(liters_1.shape, dtype=bool)
            for c in conditions
        ]

        group_arr = np.select(cond_arrs, choices, default=None)
        group_df = pd.DataFrame(
            group_arr, index=liters_1.index, columns=liters_1.columns
        )

        self.model_groups_daily = group_df
        self.model_groups_daily_dict = self._model_groups_dict_from_df(group_df)
        return self.model_groups_daily

# groups_and_tests/model_groups.py

    def create_model_groups_weekly(self):
        liters_1   = self.liters
        week_num_1 = self.weeknums
        pregnant_1 = self.pregnant
        period_1   = self.period

        # Align all frames to liters_1 by reindexing
        week_num_1 = week_num_1.reindex(index=liters_1.index, columns=liters_1.columns)
        pregnant_1 = pregnant_1.reindex(index=liters_1.index, columns=liters_1.columns)
        period_1   = period_1  .reindex(index=liters_1.index, columns=liters_1.columns)

        # pull the letter off the period label
        period_letter = period_1.apply(lambda col: col.str.extract(r'([A-Za-z]+)')[0])
        is_heifer = period_letter == 'H'
        is_dry    = period_letter == 'D'
        is_preg = pregnant_1 == 'preg'
        missing = (week_num_1.isna() | liters_1.isna()) & ~is_heifer & ~is_dry

        conditions = [
            is_heifer,
            is_dry,
            missing,
            week_num_1 < 3,
            (week_num_1 >= 3) & (liters_1 >= 15),
            (week_num_1 >= 3) & (liters_1 > 0) & (liters_1 < 15) & ~is_preg,
            (week_num_1 >= 3) & (liters_1 > 0) & (liters_1 < 15) &  is_preg,
        ]
        choices = ['H', 'D', 'G', 'F', 'A', 'B', 'C']

        # convert to plain numpy bool arrays for np.select
        cond_arrs = [
            c.to_numpy(dtype=bool, na_value=False) if not c.empty
            else np.zeros(liters_1.shape, dtype=bool)
            for c in conditions
        ]

        group_arr = np.select(cond_arrs, choices, default=None)
        group_df = pd.DataFrame(
            group_arr, 
            index=liters_1.index, 
            columns=liters_1.columns
        )

        self.model_groups_weekly = group_df
        self.model_groups_weekly_dict = self._model_groups_dict_from_df(group_df)        
        return self.model_groups_weekly

         
    def create_model_groups_monthly(self):
        liters_1   = self.liters
        week_num_1 = self.weeknums
        pregnant_1 = self.pregnant
        period_1   = self.period

        # Normalize any PeriodIndex axes to DatetimeIndex
        for df in (liters_1, week_num_1, pregnant_1, period_1):
            if isinstance(df.index, pd.PeriodIndex):
                df.index = df.index.to_timestamp()
            if isinstance(df.columns, pd.PeriodIndex):
                df.columns = df.columns.to_timestamp()

        # Resample date rows to month-end (use 'ME' for pandas >= 2.2)
        freq = 'ME'
        liters_1   = liters_1.resample(freq).last()
        week_num_1 = week_num_1.resample(freq).last()
        pregnant_1 = pregnant_1.resample(freq).last()
        period_1   = period_1.resample(freq).last()

        # Force everything to wy_id rows / date columns, matching liters_1
        if isinstance(liters_1.index, pd.DatetimeIndex):
            liters_1 = liters_1.T

        if isinstance(week_num_1.index, pd.DatetimeIndex):
            week_num_1 = week_num_1.T
        if isinstance(pregnant_1.index, pd.DatetimeIndex):
            pregnant_1 = pregnant_1.T
        if isinstance(period_1.index, pd.DatetimeIndex):
            period_1 = period_1.T

        # Align to liters_1
        week_num_1 = week_num_1.reindex(index=liters_1.index, columns=liters_1.columns)
        pregnant_1 = pregnant_1.reindex(index=liters_1.index, columns=liters_1.columns)
        period_1   = period_1  .reindex(index=liters_1.index, columns=liters_1.columns)

        # Extract period letter safely
        period_letter = period_1.astype('string').apply(
            lambda col: col.str.extract(r'([A-Za-z]+)')[0]
        )
        is_heifer = period_letter == 'H'
        is_dry    = period_letter == 'D'
        is_preg   = pregnant_1 == 'preg'
        missing   = (week_num_1.isna() | liters_1.isna()) & ~is_heifer & ~is_dry

        conditions = [
            is_heifer,
            is_dry,
            missing,
            week_num_1 < 3,
            (week_num_1 >= 3) & (liters_1 >= 15),
            (week_num_1 >= 3) & (liters_1 > 0) & (liters_1 < 15) & is_preg,
            (week_num_1 >= 3) & (liters_1 > 0) & (liters_1 < 15) & ~is_preg,
        ]
        choices = ['H', 'D', None, 'F', 'A', 'C', 'B']

        # Convert all conditions to plain numpy bool arrays
        cond_arrs = [
            c.to_numpy(dtype=bool, na_value=False) if not c.empty
            else np.zeros(liters_1.shape, dtype=bool)
            for c in conditions
        ]

        group_arr = np.select(cond_arrs, choices, default=None)
        group_df = pd.DataFrame(
            group_arr, index=liters_1.index, columns=liters_1.columns
        ).T

        self.model_groups_monthly = group_df
        self.model_groups_monthly_dict = self._model_groups_dict_from_df(group_df)        
        return self.model_groups_monthly,  self.model_groups_monthly_dict
            
    
    def _model_groups_dict_from_df(self, df):
        """Generic: takes DataFrame index=dates, columns=cow_ids, values=labels.
        Returns {group_key: {date_str: [cow_ids]}}"""
        label_to_key = {
            'H': 'heifer_ids',
            'D': 'dry_ids',
            'G': 'missing_ids',
            'F': 'fresh_ids',
            'A': 'group_A_ids',
            'B': 'group_B_ids',
            'C': 'group_C_ids',
        }

        result = {key: {} for key in label_to_key.values()}

        for date in df.index:
            date_str = pd.Timestamp(date).strftime('%Y-%m-%d')
            for cow_id, label in df.loc[date].items():
                if pd.isna(label):
                    continue
                key = label_to_key.get(label)
                if key is not None:
                    result[key].setdefault(date_str, []).append(
                        str(int(float(cow_id)))
                    )

        return result         
    
    def write_to_csv(self):
        output_dir = Path("/home/alanw/Documents/vsCode_output/model_groups")
        output_dir.mkdir(parents=True, exist_ok=True)
        self.model_groups_daily  .to_csv( output_dir / "model_groups_daily.csv")
        self.model_groups_monthly.to_csv( output_dir / "model_groups_monthly.csv")
        self.model_groups_weekly .to_csv( output_dir / "model_groups_weekly.csv")        
        
         
if __name__ == "__main__":
    obj = ModelGroups()
    obj.load()
    