'''milk_functions/milk_aggregates_basic.py'''

import inspect
import pandas as pd
from   pathlib import Path
from container import get_dependency
from   pipeline.neon.neon_connect import get_engine, read_sql_table_traced

class DailyMilkVsFullday:
    def __init__(self):
        print(f"MilkAggregatesBasic instantiated by: {inspect.stack()[1].filename}")
        self.daily_milk = pd.DataFrame()

    def load(self):
        self.engine = get_engine()        
        self.MA = get_dependency('milk_aggregates_basic')        
        self.process()
        
    def process(self):
        
        wy_total = self.MA.fullday.iloc[ -10 :, :]
        self.fullday = wy_total.sum(axis=1).rename('wy').to_frame()
        self.daily_milk, self.wy = self._read_neon_query()
        self.daily_milk_vs_fullday = self.compare_wy_cp()
        self.write_to_csv()
        

    def _read_neon_query(self):
        
        with self.engine.connect() as conn:
            daily_milk_df = read_sql_table_traced('daily_milk', conn)

            # daily_milk_df_2 = daily_milk_df_1.iloc[ -20 : , :].copy()

            daily_milk_df['datex'] = pd.to_datetime(daily_milk_df['datex'])
            self.daily_milk = daily_milk_df.sort_values('datex').reset_index(drop=True)
            self.daily_milk = daily_milk_df.rename(columns={'sale_total' : 'cp'})
            
            
            milk_totals_df = read_sql_table_traced('milk_totals', conn)
            # milk_totals_df_2 = milk_totals_df_1.iloc[-10:, :][['datex', 'total_liters']].copy()

            self.wy = milk_totals_df.rename(columns={'total_liters': 'wy'})
            self.wy['datex'] = pd.to_datetime(self.wy['datex'])
            self.wy = self.wy.sort_values('datex').set_index('datex')

            return self.daily_milk, self.wy
        
                
    def compare_wy_cp(self):
        ''' cp is from the cp receipts, wy_total is from our whiteboard'''
        diff_1 = pd.merge(self.wy,self.daily_milk,
                                  on='datex',
                                  how='left')
        diff_1['wy_heldback'] = diff_1['wy'] - diff_1['heldback_total']
        diff_1['wy_minus_cp'] = (diff_1['wy_heldback'] - diff_1['cp'])

        diff_2 = diff_1.iloc[-10 :, :]
        self.daily_milk_vs_fullday = diff_2
        return self.daily_milk_vs_fullday

        
    def write_to_csv(self):
        output_dir = Path("/home/alanw/Documents/vsCode_output/milk")
        output_dir.mkdir(parents=True, exist_ok=True)
        self.daily_milk_vs_fullday.to_csv(output_dir / "daily_milk_vs_fullday.csv")   
        
        
        
        
    
            
                
                        
                        
                        
                        
if __name__ == '__main__':
    obj = DailyMilkVsFullday()
    obj.load()                        