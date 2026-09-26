'''status_functions.status_data'''
import inspect
from pathlib import Path
import pandas as pd
from container import get_dependency


class status_data:
    def __init__(self):
        print(f"status_data instantiated by: {inspect.stack()[1].filename}")
        # load
        self.MB = None
        self.DR = None
        self.WD = None
        self._MAB = None 
        
        #process
        self.startdate = None
        self.enddate_daily = None
        self.bd = None
        self.lb = None

        
        #methods
        self.status_col = None
        self.status_col_all = None
        self.alive_ids_today = None
              

    def load(self):
        self.MB = get_dependency('milk_basics')
        self.DR = get_dependency('date_range')
        self.WD = get_dependency('wet_dry')
        self.MAB = get_dependency("milk_aggregates_basic")        
        self.process()
        
        
    def process(self):        

        self.startdate = self.DR.startdate
        self.enddate_daily =self.DR.enddate_daily     
        self.lb = self.MB.data['lb']
        self.bd = self.MB.data['bd']
        bd = self.MB.data['bd'].set_index('wy_id')
        
        self.wy_ids = self.MB.data['wy_ids']
             
          #methods
        [self.status_col, 
         self.status_col_all]       = self.create_status()
        
        self.write_to_csv()
        
              
    def create_status(self):
        ''' uses weekly data from milk_basics to determine milking groups - for the 'model_groups'''
        bd_1 = self.bd.set_index('wy_id')
        lb_1 = self.lb[['wy_id', 'b_date', 'calf_num' ]].set_index('wy_id')
        wyids = self.wy_ids
        f_1 = self.MAB.fullday
     
        wetdry_period   = self.WD.period_weekly
        wetdry_days     = self.WD.wet_dry_days_weekly
        
        fullday = f_1.loc[pd.Timestamp(self.startdate):, :].copy()        
        date_index = fullday.index
        status_col_1 = pd.DataFrame(index=date_index, columns=wyids, dtype='object')
        
        #df with the wy_id, b_dates and calf_num (all '1') for all cows that had a first calf
        lb_1_first_df = lb_1[lb_1['calf_num'] == 1]  #  & lb_1['b_date'].notna()

        # Precompute first_calf mask aligned with all wyids (True if wy in lb_1 with calf_num == 1)
        first_calf_list = lb_1_first_df.index.to_list()
        first_calf_bdate_series = lb_1_first_df['b_date']        


        #.loc returns a Series (or DataFrame slice) when the index has duplicate labels or when you pass a list/slice. It can also access multiple elements.
        #.at always returns a scalar (single value) and only works with a single row/column pair. It's faster and safer when you know you have a unique index.                             
        for wy in wyids:
            b_date = bd_1.at[wy, 'b_date']   # scalar Timestamp
            d_date = bd_1.at[wy, 'death_date']
            first_calf_bdate = first_calf_bdate_series.get(wy, pd.NaT)              
            
            for date in date_index:

                
                if date < b_date:
                    status_col_1.at[date, wy] = 'nby'
                    
                elif fullday.at[date, wy] > 0:
                    status_col_1.at[date, wy] = 'milking'
                    
                elif first_calf_list and pd.isna(first_calf_bdate):
                    status_col_1.at[date, wy] = 'heifer'
                                                           
                elif pd.notnull(d_date) and date>=d_date:
                    status_col_1.at[date, wy] = 'gone'
                    
                else: # Not milking, not nby, not gone, not heifer => dry
                    status_col_1.at[date, wy] = 'dry'
        
        self.status_col_all = status_col_1
        self.status_col = status_col_1.iloc[-1,:]
            
        return self.status_col, self.status_col_all
    
    
    def write_to_csv(self):
        output_dir = Path("/home/alanw/Documents/vsCode_output/status")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        self.status_col    .to_csv(output_dir / "status_col.csv")
    
    
if __name__ == "__main__":
    obj = status_data()
    obj.load()

        
