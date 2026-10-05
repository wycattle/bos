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
        """Label each cow-day 'preg', 'not_preg' or None.

        For a cow-day in lactation L: 'preg' if the last 'ok' ultrasound for L is
        dated before lactation L's start date, else 'not_preg'. None if the day has
        no lactation number, or the cow/lactation is missing from start_lact or
        ultra_pivot. Returns DataFrame indexed by date, columns wy_id.
        """
        dates = pd.date_range(self.startdate, self.lastday)
        wyids = pd.Index(self.MB.data['wy_ids'])

        lact = self.wd_lact_num.reindex(index=dates, columns=wyids).to_numpy(dtype=float)  # days x cows

        start = self.start_lact.reindex(wyids)
        ultra = self.ultra_pivot.reindex(wyids)
        has_start = wyids.isin(self.start_lact.index)[None, :]
        has_ultra = wyids.isin(self.ultra_pivot.index)[None, :]

        out = np.full(lact.shape, None, dtype=object)
        for L in start.columns.intersection(ultra.columns):
            in_lact = (lact == L) & has_start & has_ultra        # NaN == L is False
            is_preg = (ultra[L].notna() & (ultra[L] < start[L])).to_numpy()[None, :]
            out[in_lact & is_preg] = 'preg'
            out[in_lact & ~is_preg] = 'not_preg'

        self.preg_df_daily = pd.DataFrame(out, index=dates, columns=wyids)
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