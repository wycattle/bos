'''insem_functions\\is_pregnant.py'''
import inspect
import pandas as pd
import numpy  as np
from container import get_dependency

class IsPregnant:

    def __init__(self):

        print(f"IsPregnant instantiated by: {inspect.stack()[1].filename}")

        self.SD = None
        self.WD = None
        self.IUB = None
        self.IUD = None
        self.MB = None
        self.DR = None
        self.MA = None
        
        #process
        self.startdate = None
        self.lastday  = None
        self.milk = None
        self.wet_dry_days_daily = None
        self.period_daily = None

        self.ultra_4 = None
        self.ultra_pivot = None
        self.wd_letters = None
        self.wd_lact_num = None
        self.daynums = None
        self.liters_T = None
        self.period = None
        self.start_lact = None
        self.stop_lact = None
        self.as_of_date = None
        
        #methods
        self.wet = None
        self.preg_df_daily = None
        self.groups_count_daily = None
        self.preg_df_daily = None
        self.preg_df_weekly = None



    def load(self):

        self.SD = get_dependency('status_data')
        self.WD = get_dependency('wet_dry')
        self.IUD= get_dependency('insem_ultra_data')
        self.MB = get_dependency('milk_basics')
        self.DR = get_dependency('date_range')        
        self.MA = get_dependency('milk_aggregates')
        self.process()
        
    def process(self):
        self.startdate  = self.DR.startdate
        self.lastday    = self.MB.lastday
        
        self.milk       = self.MA.weekly_avg.copy()
        
        self.wet_dry_days_daily  = self.WD.wet_dry_days_weekly[
            self.WD.wet_dry_days_weekly.index >= pd.to_datetime(self.startdate)]\
            .reset_index().rename(columns={'index': 'date'}).set_index('date')
            
        self.period_daily = self.WD.period_weekly[
            self.WD.period_weekly.index  >= pd.to_datetime(self.startdate)]\
            .reset_index().rename(columns={'index': 'date'}).set_index('date')
            
        self.wd_letters  = self.WD.wd_letters_daily.loc [self.startdate:,:]
        self.wd_lact_num = self.WD.wd_lact_num_daily.loc[self.startdate:,:]
        
        self.daynums    = self.wet_dry_days_daily  # not needed??
        self.liters     = self.milk
        self.period     = self.period_daily.T
        
        self.start_lact = self.MB.data['start_pivot'] #cols are lact nums, rows are wy
        self.stop_lact  = self.MB.data['stop_pivot']

        #methods
        self.ultra_4, self.ultra_pivot = self.create_ultra_ok_all_dates()
        self.preg_df_daily  = self.create_preg_df_all_dates()
        self.preg_df_weekly = self.convert_preg_df_to_weekly()
  

    def create_ultra_ok_all_dates(self):

        ultra_1 = self.MB.data['u'].loc[:,['wy_id','ultra_date','calf_num','readex']].copy()
        
        # ultra_1a= ultra_1.loc[(ultra_1['wy_id'])==94,:]
        ultra_2 = ultra_1.loc[(ultra_1['readex'] == 'ok')].reset_index(drop=True)
        ultra_3 = ultra_2
        
        ultra_4a = (
            ultra_3.sort_values('ultra_date')
            .groupby(['wy_id', 'calf_num'],sort=False)
            .last()
            .reset_index()
            )
        self.ultra_4 = ultra_4a.sort_values(['wy_id', 'ultra_date']).reset_index(drop=True)
        
        ultra_5 = pd.pivot_table(self.ultra_4,
                                index = 'wy_id',
                                columns= 'calf_num',
                                values= 'ultra_date')
        self.ultra_pivot = ultra_5
        return self.ultra_4, self.ultra_pivot
    
    def create_preg_df_all_dates(self):
        dates = pd.date_range(self.startdate, self.lastday)
        wyids = self.MB.data['wy_ids']
        results = {}  # collect columns as series
        
        for i in wyids:
            preg1 = {}
            for date in dates:
                wd_lact_num = self.wd_lact_num.loc[date, i]
                
                if pd.isna(wd_lact_num):
                    preg1[date] = None
                else:
                    try:
                        start_date_date = self.start_lact.loc[i, wd_lact_num]
                    except KeyError:
                        # print(f"Missing lact column for wy_id {i}: wd_lact_num = {wd_lact_num}")
                        preg1[date] = None
                        continue
                    try:
                        ultra_date = self.ultra_pivot.loc[i, wd_lact_num]
                        if pd.notna(ultra_date) and ultra_date < start_date_date:
                            preg1[date] = 'preg'
                        else:
                            preg1[date] = 'not_preg'
                    except KeyError:
                        preg1[date] = None
            
            results[i] = pd.Series(preg1)
        
        preg_df_1 = pd.DataFrame(results)
        preg_df_1.index = pd.to_datetime(preg_df_1.index)
        self.preg_df_daily = preg_df_1.loc[ self.startdate:,: ]
        return self.preg_df_daily
    


    def convert_preg_df_to_weekly(self, freq='W-SUN'):
        """
        Resample daily pregnancy status to weekly.

        For each week/cow:
        - 'preg'      if pregnant on any day in that week
        - 'not_preg'  if observed not pregnant and never pregnant that week
        - NaN         if no observation that week
        """
        has_preg = self.preg_df_daily.eq('preg').resample(freq).max()
        has_not_preg = self.preg_df_daily.eq('not_preg').resample(freq).max()

        weekly = pd.DataFrame(
            np.nan,
            index=has_preg.index,
            columns=self.preg_df_daily.columns,
            dtype=object
        )
        weekly[has_preg] = 'preg'
        weekly[~has_preg & has_not_preg] = 'not_preg'

        self.preg_df_weekly = weekly
        return self.preg_df_weekly
        
         
if __name__ == "__main__":
    obj = IsPregnant()
    obj.load()    