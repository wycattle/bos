'''
status_functions.wet_dry
'''
import inspect
import pandas as pd
import numpy as np
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
        lacts   = self.lacts #col headers from start_pivot
        lastday = self.MB.data['lastday']
        
        idx     = self.ext_rng #starting 2016-09-01
        n_rows  = len(idx)
        day_num_array   = np.zeros((n_rows, len(wy_ids)))
        period_array    = np.full ((n_rows, len(wy_ids)), '', dtype=object)


        # outer loop iterates over wy_ids.  
            # enumerate(wy_ids) returns a sequence of tuples: (0, wy_id_0)
        for col, wy_id in enumerate(wy_ids):
            day_num_blocks = []
            label_blocks = []
            prev_stop_date = None
            prev_lact = None
            has_lactation_blocks = False
            earliest_date = None

            bd = self.bd[(self.bd['wy_id'] == wy_id)]
            b_date1 = bd['b_date']
            b_date = pd.NaT if b_date1.empty else b_date1.iloc[0]

            arrival_date = b_date
            if not bd.empty and 'arrived' in bd.columns:
                av = bd['arrived'].iloc[0]
                if pd.notna(av):
                    arrival_date = pd.Timestamp(av)

            death_date_val = pd.NaT
            if not bd.empty and 'death_date' in bd.columns:
                dd_val = bd['death_date'].iloc[0]
                try:
                    death_date_val = pd.Timestamp(dd_val)
                except (ValueError, TypeError):
                    death_date_val = pd.NaT

            # dead before data range begins -> whole span 'gone'
            if pd.notna(death_date_val) and death_date_val < idx.min():
                gone_start = idx.min()
                gone_end = min(lastday, idx.max())
                if gone_start <= gone_end:
                    n_gone = (gone_end - gone_start).days + 1
                    row_offset = idx.get_loc(gone_start)
                    n_fill = min(n_gone, n_rows - row_offset)
                    day_num_array[row_offset:row_offset + n_fill, col] = 0
                    period_array[row_offset:row_offset + n_fill, col] = 'gone'
                continue

            # --- lookahead: first lactation start date, needed to bound heifer period ---
            first_start_date = None
            for lact in lacts:
                sd = pd.to_datetime(self.start_pivot.at[wy_id, lact]
                    if (wy_id in self.start_pivot.index and lact in self.start_pivot.columns)
                    else np.nan)
                if pd.notna(sd) and sd > b_date:
                    first_start_date = pd.Timestamp(sd)
                    break

            # --- HEIFER: always the starting state, from arrival/birth to first lactation ---
            heifer_birth = arrival_date if pd.notna(arrival_date) else b_date
            if pd.notna(heifer_birth):
                heifer_end = (first_start_date - pd.Timedelta(days=1)
                            if first_start_date is not None else lastday)
                if pd.notna(death_date_val):
                    heifer_end = min(heifer_end, death_date_val)

                heifer_start = max(heifer_birth, idx.min())
                heifer_end = min(heifer_end, idx.max())

                if heifer_start <= heifer_end:
                    n_heifer = (heifer_end - heifer_start).days + 1
                    day_num_blocks.append(np.arange(1, n_heifer + 1).reshape(-1, 1))
                    label_blocks.append(np.full((n_heifer, 1), 'H', dtype=object))
                    earliest_date = heifer_start

            # --- LACTATION CYCLES: W/D alternating ---
            for lact in lacts:
                start_day = pd.to_datetime(self.start_pivot.at[wy_id, lact]
                    if (wy_id in self.start_pivot.index and lact in self.start_pivot.columns)
                    else np.nan)
                stop_day = pd.to_datetime(self.stop_pivot.at[wy_id, lact]
                    if (wy_id in self.stop_pivot.index and lact in self.stop_pivot.columns)
                    else np.nan)

                if pd.isna(start_day):
                    continue

                if (prev_stop_date is None) and (stop_day < start_day):
                    prev_stop_date = stop_day

                if prev_stop_date is not None:
                    dry_start = pd.Timestamp(prev_stop_date) + pd.Timedelta(days=1)
                    dry_end = pd.Timestamp(start_day) - pd.Timedelta(days=1)
                    if dry_start <= dry_end:
                        n_dry = (dry_end - dry_start).days + 1
                        day_num_blocks.append(np.arange(1, n_dry + 1).reshape(-1, 1))
                        label_blocks.append(np.full((n_dry, 1), f'D{prev_lact}', dtype=object))

                wet_stop = lastday if pd.isna(stop_day) else pd.Timestamp(stop_day)
                if wet_stop < pd.Timestamp(start_day):
                    prev_stop_date = None if pd.isna(stop_day) else pd.Timestamp(stop_day)
                    prev_lact = lact
                    continue

                n_wet = (wet_stop - pd.Timestamp(start_day)).days + 1
                day_num_blocks.append(np.arange(1, n_wet + 1).reshape(-1, 1))
                label_blocks.append(np.full((n_wet, 1), f'W{lact}', dtype=object))
                has_lactation_blocks = True
                if earliest_date is None:
                    earliest_date = start_day

                prev_stop_date = None if pd.isna(stop_day) else pd.Timestamp(stop_day)
                prev_lact = lact

            # --- DEATH / TRAILING PERIOD: always last ---
            if prev_stop_date is not None and prev_stop_date < lastday:
                if pd.notna(death_date_val):
                    if prev_stop_date < death_date_val:
                        dry_start = prev_stop_date + pd.Timedelta(days=1)
                        dry_end = death_date_val
                        if dry_start <= dry_end:
                            n_dry = (dry_end - dry_start).days + 1
                            day_num_blocks.append(np.arange(1, n_dry + 1).reshape(-1, 1))
                            label_blocks.append(np.full((n_dry, 1), f'D{prev_lact}', dtype=object))
                    if death_date_val < lastday:
                        gone_start = death_date_val + pd.Timedelta(days=1)
                        gone_end = lastday
                        n_gone = (gone_end - gone_start).days + 1
                        day_num_blocks.append(np.zeros((n_gone, 1)))
                        label_blocks.append(np.full((n_gone, 1), 'gone', dtype=object))
                else:
                    block_start = prev_stop_date + pd.Timedelta(days=1)
                    block_end = lastday
                    if block_start <= block_end:
                        n_dry = (block_end - block_start).days + 1
                        day_num_blocks.append(np.arange(1, n_dry + 1).reshape(-1, 1))
                        label_blocks.append(np.full((n_dry, 1), f'D{prev_lact}', dtype=object))

            # died a heifer, never lactated
            if (pd.notna(death_date_val) and death_date_val < lastday
                    and not has_lactation_blocks):
                gone_start = max(death_date_val + pd.Timedelta(days=1), idx.min())
                gone_end = min(lastday, idx.max())
                if gone_start <= gone_end:
                    n_gone = (gone_end - gone_start).days + 1
                    day_num_blocks.append(np.zeros((n_gone, 1)))
                    label_blocks.append(np.full((n_gone, 1), 'gone', dtype=object))
                if earliest_date is None:
                    earliest_date = gone_start

            if not day_num_blocks or earliest_date is None:
                continue

            stacked = np.vstack(day_num_blocks)
            stacked_labels = np.vstack(label_blocks)

            try:
                row_offset = idx.get_loc(earliest_date)
            except KeyError:
                continue

            n = stacked.shape[0]
            rows_to_fill = min(n, n_rows - row_offset)
            day_num_array[row_offset:row_offset + rows_to_fill, col] = stacked[:rows_to_fill, 0]
            period_array[row_offset:row_offset + rows_to_fill, col] = stacked_labels[:rows_to_fill, 0]


        # indentation NOW moves left to same as for col, wy_id in enumerate(wy_ids)
        wet_dry_table1      = pd.DataFrame(day_num_array, index=idx, columns=wy_ids)
        wd1                      = wet_dry_table1.T
        wd1.index                = wd1.index.astype(int)
        wd2                      = wd1.sort_index(ascending=True)
        self.wet_dry_days_daily  = wd2.T.loc[self.startdate: , :]
             
        
        period_df1   = pd.DataFrame(period_array, index=idx, columns=wy_ids).copy()
        pd1          = period_df1.T
        pd1.index    = pd1.index.astype(int)
        pd2          = pd1.sort_index(ascending=True)
        self.period_daily = pd2.T.loc[self.startdate :, :].copy()
        

           # --- get max days wetdry for each period ---
        period_labels = ['H']                                   # heifer first
        for lact in self.lacts:                                  # W1, D1, W2, D2, ...
            period_labels.append(f'W{lact}')
            period_labels.append(f'D{lact}')
        period_labels.append('gone')                             # trailing state


        max_days_per_period = pd.DataFrame(
            index=period_labels, columns=self.period_daily.columns, dtype=float
        )

        for wy_id in self.period_daily.columns:
            period = self.period_daily[wy_id]
            days   = self.wet_dry_days_daily[wy_id]
            valid  = period != ''
            max_days_per_period[wy_id] = days[valid].groupby(period[valid]).max()

        m1 = max_days_per_period.T
        m1.index = m1.index.astype(int)
        m2 = m1.sort_index(ascending=True)
        self.max_days_per_period = m2.T

        
        return self.wet_dry_days_daily, self.period_daily, self.max_days_per_period
    
        
    def reform_period_daily(self):
        ''' the self.period df comes from wet_dry and has eg W1 for each date for each cow
            This 'reform' splits the period into the W and the number: two df's 'letters' and 'wd_lact_num_weekly '''
        df = self.period_daily
        regex_pattern = r'([A-Za-z]+)(\d+)'
        #([A-Za-z]+) captures one or more letters (the W, D, whatever prefix)
        #(\d+) captures one or more digits (the number)
        self.wd_letters_daily  = df.apply(lambda col: col.str.extract(regex_pattern)[0])
        self.wd_lact_num_daily = df.apply(lambda col: col.str.extract(regex_pattern)[1]).astype(float)
        return self.wd_letters_daily, self.wd_lact_num_daily




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
    

        
    def reform_period_weekly(self):
        ''' the self.period df comes from wet_dry and has eg W1 for each date for each cow
            This 'reform' splits the period into the W and the number: two df's 'letters' and 'wd_lact_num_weekly '''
        df = self.period_weekly
        regex_pattern = r'([A-Za-z]+)(\d+)'
        #([A-Za-z]+) captures one or more letters (the W, D, whatever prefix)
        #(\d+) captures one or more digits (the number)
        self.wd_letters_weekly  = df.apply(lambda col: col.str.extract(regex_pattern)[0])
        self.wd_lact_num_weekly = df.apply(lambda col: col.str.extract(regex_pattern)[1]).astype(float)
        return self.wd_letters_weekly, self.wd_lact_num_weekly
            
    def create_wet_dry_days_weekly(self, freq='W'):
        '''Weekly aggregation of wet_dry_days (numeric) using last value.'''
        weekly_last = self.wet_dry_days_daily.resample(freq).last()

        wet_dry_days_weekly_1 = weekly_last.apply(
            lambda col: col.map(lambda x: 0 if x == 0 else (x - 1) // 7 + 1))

        wet_dry_days_weekly_2 = wet_dry_days_weekly_1[
            wet_dry_days_weekly_1.index >= self.startdate] \
                .reset_index().rename(columns={'index': 'date'}) \
                    .set_index('date')

        wet_dry_days_weekly_3 = wet_dry_days_weekly_2.T
        wet_dry_days_weekly_3.index = wet_dry_days_weekly_3.index.astype(int)
        wet_dry_days_weekly_4 = wet_dry_days_weekly_3.sort_index(ascending=True).T

        self.wet_dry_days_weekly = wet_dry_days_weekly_4

        return self.wet_dry_days_weekly


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