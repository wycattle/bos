'''milk_functions/milk_aggregates_basic.py

Loads milk data from Neon (milk_transpose table), computes AM/PM/fullday matrices,
and injects MB.data['milk'] with the freshly computed fullday.
No insem dependency — safe to load before status_data.
'''

# import sys
# import os
# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import inspect
import pandas as pd
import numpy as np

from container import get_dependency
from   pipeline.neon.neon_connect import get_engine, read_sql_table_traced


class MilkAggregatesBasic:

    def __init__(self):
        print(f"MilkAggregatesBasic instantiated by: {inspect.stack()[1].filename}")
        self.MB = None
        self.data = None
        self.lag = -10
        self.maxcols = None
        self.idx_am = None
        self.idx_pm = None
        self.wy_am_np = None
        self.wy_pm_np = None
        self.liters_am_np = None
        self.liters_pm_np = None
        self.am = None
        self.pm = None
        self.fullday_preClean = None
        self.fullday_lastdate = None
        self.AM_liters = None
        self.AM_wy = None
        self.PM_liters = None
        self.PM_wy = None
        self.datex = None
        self.start_pivot = None
        self.stop_pivot = None

    def load(self):
        self.MB     = get_dependency('milk_basics')
        self.DR     = get_dependency('date_range')
        self.process()
        
    def process(self):
      
        self.data = self.MB.data
        self.start_pivot = self.MB.data['start_pivot']
        self.stop_pivot  = self.MB.data['stop_pivot']
        self.start_date  = self.DR.startdate

        # Methods

        [self.maxcols, self.idx_am, self.idx_pm,
         self.wy_am_np, self.wy_pm_np,
         self.liters_am_np, self.liters_pm_np
         ] = self.basics()

        [self.am, self.pm, 
         self.fullday_preClean,
         self.fullday_lastdate] = self.fullday_calc()
        
        [self.fullday, 
         self.fullday_row_sum, 
         self.fullday_col_sum,
         self.fullday_milking_count] = self.fullday_interpolation()
        
        self.fullday_stats = self.create_fullday_stats()

        # MB milk gets populated here to avoice circularity
        self.MB.data['milk'] = self.fullday_preClean

    def basics(self):
        # Read milk_transpose from Neon — four targeted queries
        engine = get_engine()
        with engine.connect() as conn:
            def _read_type(type_name):
                sql = f"SELECT * FROM milk_transpose WHERE type = '{type_name}' ORDER BY date"
                return (pd.read_sql(sql, conn)
                          .drop(columns=['type'])
                          .set_index('date')  #this is the first col 'name' in neon milk_transpose
                          .T)

            self.AM_liters = _read_type('AM_liters')
            self.AM_wy     = _read_type('AM_wy')
            self.PM_liters = _read_type('PM_liters')
            self.PM_wy     = _read_type('PM_wy')

        self.datex = pd.to_datetime(self.AM_liters.columns, errors="coerce")
        print('last index value ', self.datex[-1])

        self.maxcols = len(self.datex)
        maxrows      = len(self.data['bd']['wy_id'])

        idx          = np.zeros((maxrows + 1, self.maxcols), dtype=int)
        self.idx_am  = idx.copy()
        self.idx_pm  = idx.copy()

        self.wy_am_np     = self.AM_wy    .to_numpy(dtype=float)
        self.wy_pm_np     = self.PM_wy    .to_numpy(dtype=float)
        self.liters_am_np = self.AM_liters.to_numpy(dtype=float)
        self.liters_pm_np = self.PM_liters.to_numpy(dtype=float)
        
        bd = self.data['bd'].set_index('wy_id')
        last_date = self.datex[-1]


        return [self.maxcols, self.idx_am, self.idx_pm,
                self.wy_am_np, self.wy_pm_np,
                self.liters_am_np, self.liters_pm_np
                ]
        
        

    def fullday_calc(self):
        # AM calc
        target_am = []
        for i in range(self.maxcols):
            index2  = np.nan_to_num(self.wy_am_np[:, i],     nan=0).astype(int)
            value2  = np.nan_to_num(self.liters_am_np[:, i], nan=0.0).astype(float)
            target1 = self.idx_am[:, i].astype(float)
            target1[index2] = value2
            target_am.append(target1)
        am1 = pd.DataFrame(target_am)
        
        self.am = am1.T
        # self.am.columns = self.AM_liters.columns
        self.am.columns = pd.to_datetime(self.AM_liters.columns, errors='coerce')
        self.am.replace(0, np.nan, inplace=True)
        self.am.drop(self.am.columns[0], axis=1, inplace=True)
        am_test = self.am.loc[94,'2025-05-01':].copy()
        
        

        # PM calc
        target_pm = []
        for i in range(self.maxcols):
            index2  = np.nan_to_num(self.wy_pm_np[:, i],     nan=0).astype(int)
            value2  = np.nan_to_num(self.liters_pm_np[:, i], nan=0.0).astype(float)
            target1 = self.idx_pm[:, i].astype(float)
            target1[index2] = value2
            target_pm.append(target1)
        pm1 = pd.DataFrame(target_pm)

        self.pm = pm1.T
        self.pm.columns = self.datex
        self.pm.replace(0, np.nan, inplace=True)
        self.pm.drop(self.pm.columns[0], axis=1, inplace=True)
        print('last pm ', self.pm.iloc[-1,93:95])




        # fullday calc
        fullday1 = np.add(am1, pm1)
        fullday2 = pd.DataFrame(fullday1)
        fullday2['datex'] = self.datex
        fullday2.set_index('datex', inplace=True)

        fullday2.index = pd.to_datetime(fullday2.index, errors='coerce')  # ISO format from Neon
        fullday2.replace(0, np.nan, inplace=True)
        fullday2.drop(fullday2.iloc[:, 0:1], axis=1, inplace=True)
        fullday2.index.name = 'datex'

        self.fullday_lastdate = pd.DataFrame(
            index=[fullday2.index[-1]], columns=['last_date'])
        
        self.fullday_preClean = fullday2
        return [self.am, self.pm, self.fullday_preClean, self.fullday_lastdate]





    def fullday_interpolation(self):
 
        
        if 'wy_id' in self.start_pivot.columns:
            start_pivot = self.start_pivot.set_index('wy_id')
        else: 
            self.start_pivot
            
        if 'wy_id' in self.stop_pivot.columns:
            stop_pivot  = self.stop_pivot.set_index('wy_id')  
        else: self.stop_pivot

        lac_cols = [c for c in self.start_pivot.columns if c in self.stop_pivot.columns]

        dates = self.fullday_preClean.index.values.astype('datetime64[ns]')          # (D,)
        wy_ids = self.fullday_preClean.columns                                        # (W,)
        last_date = dates.max()

        starts_mat = self.start_pivot.reindex(wy_ids)[lac_cols].values            # (W, L)
        stops_mat  = self.stop_pivot .reindex(wy_ids)[lac_cols].values             # (W, L)
        stops_mat  = np.where(pd.isna(stops_mat), last_date, stops_mat)      # open lactations -> last_date

        wet_mask = np.zeros((len(dates), len(wy_ids)), dtype=bool)           # (D, W)

        for i in range(len(lac_cols)):
            starts = starts_mat[:, i].astype('datetime64[ns]')               # (W,)
            stops  = stops_mat[:, i].astype('datetime64[ns]')                # (W,)
            valid  = ~pd.isna(starts)
            window = (dates[:, None] >= starts[None, :]) & (dates[:, None] <= stops[None, :])
            wet_mask |= window & valid[None, :]

        fullday_wet_mask = pd.DataFrame(wet_mask, index=self.fullday_preClean.index, columns=self.fullday_preClean.columns)

        # interpolate the whole grid, then only KEEP the fill where it falls inside a real lactation window
        interpolated = self.fullday_preClean.interpolate(method='linear', limit_area='inside', axis=0)

        fullday_imputed_mask = self.fullday_preClean.isna() & fullday_wet_mask & interpolated.notna()
        fullday_clean_1 = self.fullday_preClean.where(~fullday_wet_mask, interpolated)
        
        self.fullday = fullday_clean_1.loc[self.start_date :, :]
        self.fullday_row_sum = fullday_clean_1.sum(axis=1)
        self.fullday_col_sum = fullday_clean_1.sum(axis=0)
        self.fullday_milking_count = (fullday_clean_1 > 0).sum(axis=0)

        return self.fullday, self.fullday_row_sum, self.fullday_col_sum, self.fullday_milking_count
    
    
    def create_fullday_stats(self):
        
        col_sum = self.fullday_col_sum
        count = self.fullday_milking_count
        avg = col_sum / count
        
        stats = pd.concat([col_sum, count, avg], axis=1)
        stats.columns = ['liters', 'count', 'avg']
        stats.index.name = 'wy_id'
        stats = stats.reset_index()
        self.fullday_stats = stats
        return self.fullday_stats


if __name__ == '__main__':
    obj = MilkAggregatesBasic()
    obj.load()