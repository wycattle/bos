'''
status_functions.wet_dry
'''
import inspect
import pandas as pd
import numpy as np
import re
from pathlib import Path
from container import get_dependency

today = pd.Timestamp.today()

class WetDry:
    ''' returns the 'period' W1, D1 etc, and the days '''
        
    def __init__(self):
        print(f"WetDry instantiated by: {inspect.stack()[1].filename}")

        # load
        self.MB = None
        
        #process
        self.data = None
        self.death_date = None
        self.ext_rng = None
        self.datex = None        
        self.startdate = None
        
        self.milk1 = None
        self.bd = None
        self.start_pivot = None
        self.stop_pivot = None
        self.wy_id_list = None
        self.lacts = None
        
        #methods
        self.period_daily = None
        self.max_days_per_period = None
        self.wd_letters_daily = None 
        self.wd_lact_num_daily = None
        self.period_weekly      = None
        self.wet_period_weekly  = None
        self.wet_dry_days_weekly = None
        self.wet_dry_days_daily = None
        self.wd_letters_weekly = None 
        self.wd_lact_num_weekly = None

        
    def load(self):
        self.MB = get_dependency('milk_basics')
    
        # Get fullday DataFrame from MilkAggregatesBasic and reindex to extended date range
        # Columns are integer indices from numpy; convert to strings to match str(wy_id) lookups
        self.MAB = get_dependency('milk_aggregates_basic')
        self.DR = get_dependency('date_range')
        self.process()
        
    def process(self):
        self.data       = self.MB.data
        self.death_date = self.MB.bd[['wy_id','death_date']]
        self.ext_rng    = self.MB.data['ext_rng']
        self.datex      = self.MB.data['datex']
        # self.startdate  = self.DR.startdate
        self.startdate  = pd.to_datetime("2016-09-01")
      
        fullday         = self.MAB.fullday.copy()
        fullday.columns = fullday.columns.astype(str)
        self.milk1      = fullday.reindex(self.MB.data['ext_rng'])      
      
        self.bd = self.MB.data['bd']
        
        self.start_pivot = self.MB.data['start_pivot']
        self.stop_pivot  = self.MB.data['stop_pivot']

        self.wy_id_list = self.start_pivot.index
        self.lacts      = self.start_pivot.columns    

        #methods
        (self.wet_dry_days_daily, 
         self.period_daily, 
         self.max_days_per_period)  = self.create_wet_dry_daily()
        
        (self.wd_letters_daily, 
        self.wd_lact_num_daily)     = self.reform_period_daily()
        
        
        (self.wet_period_weekly, 
         self.period_weekly)        = self.create_period_weekly()
        
        (self.wd_letters_weekly, 
         self.wd_lact_num_weekly)   = self.reform_period_weekly()
        
        self.wet_dry_days_weekly    = self.create_wet_dry_days_weekly()
        self.write_to_csv()
        

    def create_wet_dry_daily(self):
        '''  returns self.wet_dry_days_daily, self.period_daily  '''
        wy_ids  = self.MB.data['wy_ids']
        lacts   = list(self.lacts)
        lastday = self.MB.data['lastday']

        idx    = self.ext_rng
        n_rows = len(idx)
        n_cols = len(wy_ids)
        day_num_array = np.zeros((n_rows, n_cols))
        period_array  = np.full((n_rows, n_cols), '', dtype=object)

        # ---- pre-compute everything as numpy datetime64 (no per-cow pandas .at) ----
        bd_idx = self.bd.drop_duplicates('wy_id').set_index('wy_id')

        def _col(name):
            if name in bd_idx.columns:
                return pd.to_datetime(bd_idx[name].reindex(wy_ids), errors='coerce')
            return pd.Series(pd.NaT, index=wy_ids)

        def _pivot_to_np(df):
            '''DataFrame (object dtype: Timestamps/NaN) -> 2D datetime64 array.
            Per-column conversion sidesteps pandas 3.x stack() API changes.'''
            d = df.reindex(index=wy_ids, columns=lacts)
            cols = [
                pd.to_datetime(d[c], errors='coerce').to_numpy(dtype='datetime64[ns]')
                for c in d.columns
            ]
            return (np.column_stack(cols) if cols
                    else np.empty((len(d), 0), dtype='datetime64[ns]'))


        b_date_s  = _col('b_date')
        arriv_s   = _col('arrived')
        death_s   = _col('death_date')

        birth_np  = b_date_s.to_numpy(dtype='datetime64[ns]')
        arriv_np  = arriv_s.to_numpy(dtype='datetime64[ns]')
        death_np  = death_s.to_numpy(dtype='datetime64[ns]')

        start_np  = _pivot_to_np(self.start_pivot)
        stop_np   = _pivot_to_np(self.stop_pivot)
        n_lacts   = len(lacts)

        idx_np     = idx.to_numpy(dtype='datetime64[ns]')
        idx_min    = idx_np[0]
        idx_max    = idx_np[-1]
        lastday_np = np.datetime64(pd.Timestamp(lastday), 'ns')
        ONE_DAY    = np.timedelta64(86_400_000_000_000, 'ns')   


        for col, wy_id in enumerate(wy_ids):
            b_date  = birth_np[col]
            av      = arriv_np[col]
            arrival_date = av if not np.isnat(av) else b_date
            death_date_val = death_np[col]

            # dead before data range begins -> whole span 'gone'
            if (not np.isnat(death_date_val)) and death_date_val < idx_min:
                gone_start, gone_end = idx_min, min(lastday_np, idx_max)
                if gone_start <= gone_end:
                    n_gone = int((gone_end - gone_start) / ONE_DAY) + 1
                    row_offset = int(np.searchsorted(idx_np, gone_start))
                    n_fill = min(n_gone, n_rows - row_offset)
                    period_array[row_offset:row_offset + n_fill, col] = 'gone'
                continue

            # lookahead: first lactation start (bounds heifer)
            first_start = None
            for j in range(n_lacts):
                sd = start_np[col, j]
                if (not np.isnat(sd)) and sd > b_date:
                    first_start = sd
                    break

            day_num_blocks, label_blocks = [], []
            earliest_date = None
            prev_stop = None
            prev_lact = None
            has_lact  = False

            # --- HEIFER ---
            heifer_birth = arrival_date if not np.isnat(arrival_date) else b_date
            if not np.isnat(heifer_birth):
                heifer_end = (first_start - ONE_DAY) if first_start is not None else lastday_np
                if not np.isnat(death_date_val):
                    heifer_end = min(heifer_end, death_date_val)
                hs = max(heifer_birth, idx_min)
                he = min(heifer_end, idx_max)
                if hs <= he:
                    n_h = int((he - hs) / ONE_DAY) + 1
                    day_num_blocks.append(np.arange(1, n_h + 1).reshape(-1, 1))
                    label_blocks.append(np.full((n_h, 1), 'H', dtype=object))
                    earliest_date = hs

            # --- LACTATION CYCLES ---
            for j, lact in enumerate(lacts):
                start_day = start_np[col, j]
                stop_day  = stop_np[col, j]
                if np.isnat(start_day):
                    continue

                if prev_stop is None and (not np.isnat(stop_day)) and stop_day < start_day:
                    prev_stop = stop_day

                if prev_stop is not None:
                    dry_start = prev_stop + ONE_DAY
                    dry_end   = start_day - ONE_DAY
                    if dry_start <= dry_end:
                        n_d = int((dry_end - dry_start) / ONE_DAY) + 1
                        day_num_blocks.append(np.arange(1, n_d + 1).reshape(-1, 1))
                        label_blocks.append(np.full((n_d, 1), f'D{prev_lact}', dtype=object))

                wet_stop = lastday_np if np.isnat(stop_day) else stop_day
                if wet_stop < start_day:
                    prev_stop = None if np.isnat(stop_day) else stop_day
                    prev_lact = lact
                    continue

                n_w = int((wet_stop - start_day) / ONE_DAY) + 1
                day_num_blocks.append(np.arange(1, n_w + 1).reshape(-1, 1))
                label_blocks.append(np.full((n_w, 1), f'W{lact}', dtype=object))
                has_lact = True
                if earliest_date is None:
                    earliest_date = start_day

                prev_stop = None if np.isnat(stop_day) else stop_day
                prev_lact = lact

            # --- DEATH / TRAILING ---
            if prev_stop is not None and prev_stop < lastday_np:
                if not np.isnat(death_date_val):
                    if prev_stop < death_date_val:
                        dry_start, dry_end = prev_stop + ONE_DAY, death_date_val
                        if dry_start <= dry_end:
                            n_d = int((dry_end - dry_start) / ONE_DAY) + 1
                            day_num_blocks.append(np.arange(1, n_d + 1).reshape(-1, 1))
                            label_blocks.append(np.full((n_d, 1), f'D{prev_lact}', dtype=object))
                    if death_date_val < lastday_np:
                        gone_start, gone_end = death_date_val + ONE_DAY, lastday_np
                        n_g = int((gone_end - gone_start) / ONE_DAY) + 1
                        day_num_blocks.append(np.zeros((n_g, 1)))
                        label_blocks.append(np.full((n_g, 1), 'gone', dtype=object))
                else:
                    block_start, block_end = prev_stop + ONE_DAY, lastday_np
                    if block_start <= block_end:
                        n_d = int((block_end - block_start) / ONE_DAY) + 1
                        day_num_blocks.append(np.arange(1, n_d + 1).reshape(-1, 1))
                        label_blocks.append(np.full((n_d, 1), f'D{prev_lact}', dtype=object))

            if (not np.isnat(death_date_val)) and death_date_val < lastday_np and not has_lact:
                gone_start = max(death_date_val + ONE_DAY, idx_min)
                gone_end   = min(lastday_np, idx_max)
                if gone_start <= gone_end:
                    n_g = int((gone_end - gone_start) / ONE_DAY) + 1
                    day_num_blocks.append(np.zeros((n_g, 1)))
                    label_blocks.append(np.full((n_g, 1), 'gone', dtype=object))
                if earliest_date is None:
                    earliest_date = gone_start

            if not day_num_blocks or earliest_date is None:
                continue

            stacked        = np.vstack(day_num_blocks)
            stacked_labels = np.vstack(label_blocks)
            row_offset     = int(np.searchsorted(idx_np, earliest_date))
            n              = stacked.shape[0]
            rows_to_fill   = min(n, n_rows - row_offset)
            day_num_array[row_offset:row_offset + rows_to_fill, col] = stacked[:rows_to_fill, 0]
            period_array [row_offset:row_offset + rows_to_fill, col] = stacked_labels[:rows_to_fill, 0]

        # ---- assemble outputs (same as before) ----
        wet_dry_table1 = pd.DataFrame(day_num_array, index=idx, columns=wy_ids)
        wd1 = wet_dry_table1.T
        wd1.index = wd1.index.astype(int)
        wd2 = wd1.sort_index(ascending=True)
        self.wet_dry_days_daily = wd2.T.loc[self.startdate:, :]

        period_df1 = pd.DataFrame(period_array, index=idx, columns=wy_ids).copy()
        pd1 = period_df1.T
        pd1.index = pd1.index.astype(int)
        pd2 = pd1.sort_index(ascending=True)
        self.period_daily = pd2.T.loc[self.startdate:, :].copy()

        # ---- max days per period : vectorised (was a per-cow groupby loop) ----
        period_labels = ['H']  # H only occurs once, so no need to increment
        for lact in lacts:
            period_labels += [f'W{lact}', f'D{lact}']
        period_labels.append('gone')

        p_long = self.period_daily.stack()
        d_long = self.wet_dry_days_daily.stack()
        mask   = p_long != ''
        long   = pd.DataFrame({'period': p_long[mask], 'days': d_long[mask]})

        m = long.groupby([long.index.get_level_values(1), 'period'])['days'].max().unstack('period')
        m.index = m.index.astype(int)
        m = m.sort_index()
        m = m.reindex(columns=period_labels)
        m.index.name = 'wy_id'
        m = m.reset_index()
        m = m.drop(columns=['gone'])
        
        self.max_days_per_period = m
        

        return self.wet_dry_days_daily, self.period_daily, self.max_days_per_period      
        

#-----WEEKLY CONVERSION-----**********************************************

    def create_period_weekly(self, freq='W'):
        
        ''' converts the daily df self.period_daily to weekly'''
        
        period_weekly_1 = self.period_daily.resample(freq).last()
        period_weekly_2 = period_weekly_1.T
        period_weekly_2.index = period_weekly_2.index.astype(int)
        period_weekly_3 = period_weekly_2.sort_index(ascending=True)
        period_weekly_4 = period_weekly_3.T
        
        self.period_weekly = period_weekly_4
            
        self.wet_period_weekly = period_weekly_4[
            period_weekly_4.index  >= self.startdate] \
                .reset_index().rename(columns={'index': 'date'}) \
                    .set_index('date') 
                    

        return self.wet_period_weekly, self.period_weekly, 
    

    def create_wet_dry_days_weekly(self, freq='W'):
        '''Weekly aggregation of wet_dry_days (numeric) using last value.'''
        weekly_last = self.wet_dry_days_daily.resample(freq).last()

        # vectorised replacement for: col.map(lambda x: 0 if x == 0 else (x - 1)//7 + 1)
        arr = weekly_last.to_numpy(dtype=float)
        arr = np.where(arr == 0, 0.0, (arr - 1) // 7 + 1)
        weekly_last = pd.DataFrame(arr, index=weekly_last.index, columns=weekly_last.columns)

        weekly_2 = weekly_last[weekly_last.index >= self.startdate] \
            .reset_index().rename(columns={'index': 'date'}).set_index('date')

        weekly_3 = weekly_2.T
        weekly_3.index = weekly_3.index.astype(int)
        self.wet_dry_days_weekly = weekly_3.sort_index(ascending=True).T

        return self.wet_dry_days_weekly

    # --- shared fast regex splitter: only N unique labels, so map once ---
    _PERIOD_RE = re.compile(r'^([A-Za-z]+)(\d+)$')

    @classmethod
    def _split_periods(cls, df):
        arr  = df.to_numpy()
        uniq = pd.unique(arr.ravel())
        letters, nums = {}, {}
        for v in uniq:
            m = cls._PERIOD_RE.match(str(v))
            if m:
                letters[v] = m.group(1)
                nums[v]    = float(m.group(2))
            else:
                letters[v] = np.nan
                nums[v]    = np.nan
        L = pd.Series(letters).reindex(arr.ravel()).to_numpy().reshape(arr.shape)
        N = pd.Series(nums   ).reindex(arr.ravel()).to_numpy().reshape(arr.shape)
        return (pd.DataFrame(L, index=df.index, columns=df.columns),
                pd.DataFrame(N, index=df.index, columns=df.columns))


    def reform_period_daily(self):
        self.wd_letters_daily, self.wd_lact_num_daily = self._split_periods(self.period_daily)
        return self.wd_letters_daily, self.wd_lact_num_daily


    def reform_period_weekly(self):
        self.wd_letters_weekly, self.wd_lact_num_weekly = self._split_periods(self.period_weekly)
        return self.wd_letters_weekly, self.wd_lact_num_weekly



    def write_to_csv(self):
        output_dir = Path("/home/alanw/Documents/vsCode_output/wet_dry")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        self.wet_dry_days_weekly    .to_csv(output_dir / "wet_dry_days_weekly.csv")
        self.wd_letters_daily       .to_csv(output_dir / "wd_letters_daily.csv")
        self.wd_lact_num_daily      .to_csv(output_dir / "wd_lact_num_daily.csv")
        self.period_weekly          .to_csv(output_dir / "period_weekly.csv")
        self.wet_period_weekly      .to_csv(output_dir / "wet_period_weekly.csv")
        self.wet_dry_days_daily     .to_csv(output_dir / "wet_dry_days_daily.csv")
        self.period_daily           .to_csv(output_dir / "period_daily.csv")
        self.max_days_per_period    .to_csv(output_dir / "max_days_per_period.csv")     

if __name__ == '__main__':
    obj=WetDry()
    obj.load()      