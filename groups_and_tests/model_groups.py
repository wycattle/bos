'''milk_functions\\model_groups.py'''
import inspect
import pandas as pd
import numpy as np
from pathlib import Path
from container import get_dependency

        
_LABEL_TO_KEY = {
    'H': 'heifer_ids', 'D': 'dry_ids', 'G': 'missing_ids', 'F': 'fresh_ids',
    'A': 'group_A_ids', 'B': 'group_B_ids', 'C': 'group_C_ids',
}

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
        
        
        # methods
        # self.create_model_groups_daily()
        # self.create_model_groups_weekly()
        # self.create_model_groups_monthly()
        self.create_model_groups()

    def create_model_groups(self):
        weekly = self._classify()
        for df in (weekly,):                      # PeriodIndex -> timestamps, as before
            if isinstance(df.index, pd.PeriodIndex):
                df.index = df.index.to_timestamp()
        monthly = weekly.resample('ME').last()    # label of last non-null week in month

        self.model_groups_weekly  = weekly
        self.model_groups_daily   = weekly        # same grid; drop if nothing reads it
        self.model_groups_monthly = monthly
        self.model_groups_weekly_dict  = self._model_groups_dict_from_df(weekly)
        self.model_groups_daily_dict   = self.model_groups_weekly_dict
        self.model_groups_monthly_dict = self._model_groups_dict_from_df(monthly)       


    def _classify(self):
        """Group label per cow-week: H heifer, D dry, G missing, F fresh (<3 wk),
        A (>=15 L), C (<15 L, pregnant), B (<15 L, not pregnant).
        Returns DataFrame (dates x cows, object)."""
        liters = self.liters
        ix = dict(index=liters.index, columns=liters.columns)   # 'index' is the weekly date index
        wk     = self.weeknums.reindex(**ix).to_numpy(dtype=float)
        L      = liters.to_numpy(dtype=float)
        period = self.period.reindex(**ix).astype('string')
        letter = period.apply(lambda c: c.str.extract(r'([A-Za-z]+)')[0])

        def arr(c): return c.to_numpy(dtype=bool, na_value=False)
        heifer = arr(letter == 'H')
        dry    = arr(letter == 'D')
        preg   = arr(self.pregnant.reindex(**ix) == 'preg')
        missing = (np.isnan(wk) | np.isnan(L)) & ~heifer & ~dry
        lact = wk >= 3

        out = np.select(
            [heifer, dry, missing, wk < 3,
            lact & (L >= 15),
            lact & (L > 0) & (L < 15) & preg,
            lact & (L > 0) & (L < 15) & ~preg],
            ['H', 'D', 'G', 'F', 'A', 'C', 'B'], default=None)
        return pd.DataFrame(out, dtype=object, **ix)




    def _model_groups_dict_from_df(self, df):
        """Invert a label grid into id lists per group and date.

        df: index=dates, columns=cow ids, values=group labels (NaN/None skipped).
        Returns {group_key: {'YYYY-MM-DD': [cow_id_str, ...]}}; every group key is
        present, and unmapped labels are ignored.
        """
        long = (df.stack().dropna()
                .rename_axis(['date', 'cow']).rename('label').reset_index())
        long['key'] = long['label'].map(_LABEL_TO_KEY)
        long = long.dropna(subset=['key'])
        long['date'] = pd.to_datetime(long['date']).dt.strftime('%Y-%m-%d')
        long['cow'] = long['cow'].astype(float).astype(int).astype(str)

        result = {k: {} for k in _LABEL_TO_KEY.values()}
        for (key, date), cows in long.groupby(['key', 'date'], sort=False)['cow']:
            result[key][date] = cows.tolist()
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
    obj.write_to_csv()
    