'''status_functions.status_data'''
import inspect
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime
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
        self.alive_ids_today_list = None
              

    def load(self):
        self.MB = get_dependency('milk_basics')
        self.DR = get_dependency('date_range')
        self.WD = get_dependency('wet_dry')
        self.MAB = get_dependency("milk_aggregates_basic")        
        self.process()
        
        
    def process(self):        

        self.startdate = self.DR.startdate
        self.enddate_daily =self.DR.enddate_daily     
        self.lb = self.MB.data['lb'].copy()
        self.bd = self.MB.data['bd'].copy()
        self.bd = self.MB.data['bd'].set_index('wy_id')
        
        self.wy_ids = self.MB.data['wy_ids']
             
          #methods
        self.wy_age = self.create_age_wy()
        
        [self.status_col, 
         self.status_col_all]       = self.create_status()
        
        self.alive_ids_today_list   = self.create_alive_ids_today()
        
        self.write_to_csv()


    def create_age_wy(self):    # age_wy means age since it arrived ...
        today   = pd.Timestamp.now().normalize()
        bd      = self.bd.reset_index()
        b_date  = pd.to_datetime(bd['b_date'])
        d_date  = pd.to_datetime(bd['death_date'])
        adj_bdate = pd.to_datetime(bd['adj_bdate'])
        
        # vectorized: dead cows = (death_date - b_date), alive = (today - b_date)
        # numpy.where(condition, [x, y, ]/) ie np.where(condition, if_true, if_false)  
        # and the / at the end means: This slash forbids keyword arguments!
        condition = d_date.notna() #death date exists
        
        age = np.where(
                condition,          #the condition
                d_date - adj_bdate, #this is the True half of the bool
                today - adj_bdate,  #this is the False half of the bool
            )
        bd['wy_age'] = bd['wy_age'] = pd.Series(age).dt.days.astype('Int64')
        
        self.wy_age = bd
        
        return    self.wy_age
        

    def create_status(self):
        bd_1 = self.bd
        wyids = list(self.wy_ids)
        fullday = self.MAB.fullday.loc[pd.Timestamp(self.startdate):, :]
        date_index = fullday.index

        # per-cow vectors (shape 1 x n_cows)
        b_date = pd.to_datetime(bd_1.loc[wyids, 'b_date']).to_numpy()[None, :]
        d_date = pd.to_datetime(bd_1.loc[wyids, 'death_date']).to_numpy()[None, :]

        first = self.lb.loc[self.lb['calf_num'] == 1, ['wy_id', 'b_date']].drop_duplicates('wy_id')
        first_bdate = first.set_index('wy_id')['b_date'].reindex(wyids)
        # keeps your original logic: heifer only if any first-calf rows exist at all
        heifer = (len(first) > 0) & first_bdate.isna().to_numpy()[None, :]

        # per-date / cell matrices (n_dates x n_cows)
        dates = date_index.to_numpy()[:, None]
        milking = (fullday.reindex(columns=wyids).to_numpy() > 0)   # NaN -> False
        nby = dates < b_date
        gone = dates >= d_date                                        # NaT -> False

        arr = np.select(
            [nby, milking, heifer, gone],
            ['nby', 'milking', 'heifer', 'gone'],
            default='dry',
        )
        self.status_col_all = pd.DataFrame(arr, index=date_index, columns=wyids, dtype='object')
        self.status_col = self.status_col_all.iloc[-1, :].copy()
        return self.status_col, self.status_col_all
    
    
    def create_alive_ids_today(self):
        status_list = ['nby','milking','heifer','gone','dry']
        sct = self.status_col
        alive_ids = sct[sct.isin(['milking','dry'])].index.to_list()
        self.alive_ids_today_list = alive_ids
        
        return self.alive_ids_today_list
    
    
    
    
    def write_to_csv(self):
        output_dir = Path("/home/alanw/Documents/vsCode_output/status")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        self.status_col     .to_csv( output_dir / "status_col.csv")
        self.status_col_all .to_csv( output_dir / "status_col_all.csv")
        self.wy_age         .to_csv( output_dir / "wy_age.csv")
    
    
if __name__ == "__main__":
    obj = status_data()
    obj.load()

        
