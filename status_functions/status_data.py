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
        self.lb_pivot = self.MB.data['live_birth_pivot']

        self.bd = self.MB.data['bd'].copy().set_index('wy_id')
        
        self.wy_ids = self.MB.data['wy_ids']
             
          #methods
        self.wy_age = self.create_age_wy()
        
        [self.status_col, 
         self.status_col_all]       = self.create_status()
        
        self.alive_ids_today_list   = self.create_alive_ids_today()


    def create_age_wy(self):    # age_wy means age since it arrived ...
        today   = pd.Timestamp.now().normalize()
        bd      = self.bd.copy()
        d_date      = pd.to_datetime(bd['death_date'])
        adj_bdate   = pd.to_datetime(bd['adj_bdate']) # the col in birth_death
        
        # vectorized: dead cows = (death_date - b_date), alive = (today - b_date)
        # numpy.where(condition, [x, y, ]/) ie np.where(condition, if_true, if_false)  
        # and the / at the end means: This slash forbids keyword arguments!
        condition = d_date.notna() #death date exists

        # creates ndarray (321,)
        age = np.where(
                condition,          #the condition
                d_date - adj_bdate, # is True 
                today - adj_bdate,  # is False 
            )

        #bd is a df and the new col is days alive for both gone and not gone cows
        bd['wy_age'] = bd['wy_age'] = pd.Series(age).dt.days.astype('Int64')

        
        self.wy_age = bd
        
        return    self.wy_age
        

    def create_status(self):
        wyids = list(self.wy_ids)

        # dates for the status period
        fullday = self.MAB.fullday.loc[pd.Timestamp(self.startdate):, :]
        dates = fullday.index

        # everything reindexed to wyids -> identical column order by construction
        bd = self.bd.reindex(wyids)
        first_bdate = pd.to_datetime(self.lb_pivot[1].reindex(wyids))
        b_date = pd.to_datetime(bd['b_date'])
        d_date = pd.to_datetime(bd['death_date'])
        milk = fullday.reindex(columns=wyids)

        assert list(bd.index) == list(first_bdate.index) == list(milk.columns) == wyids

        # arrays: (n_dates, 1) vs (1, n_cows) -> broadcast to (n_dates, n_cows)
        date_idx = dates.to_numpy()[:, None]
        b_np = b_date.to_numpy()[None, :]
        d_np = d_date.to_numpy()[None, :]
        fb_np = first_bdate.to_numpy()[None, :]

        milking = milk.to_numpy() > 0                          # NaN -> False
        nby = date_idx < b_np                                  # not born yet
        gone = date_idx >= d_np                                # NaT -> False (still alive)
        heifer = first_bdate.isna().to_numpy()[None, :] | (date_idx < fb_np)

        arr = np.select(
            [nby, gone, milking, heifer],
            ['nby', 'gone', 'milking', 'heifer'],
            default='dry',
        )

        self.status_col_all = pd.DataFrame(arr, index=dates, columns=wyids, dtype='object')
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

        sca = self.status_col_all.copy()
        scat = sca[sca.index >='2023-01-01']
        self.status_col     .to_csv( output_dir / "status_col.csv")
        scat                .to_csv( output_dir / "status_col_all.csv")
        self.wy_age         .to_csv( output_dir / "wy_age.csv")
        self.lb_pivot       .to_csv( output_dir / "lb_pivot.csv")
    
    
if __name__ == "__main__":
    obj = status_data()
    obj.load()
    obj.write_to_csv()
    cow = 15  # change to str if wy_ids are strings
    sca = obj.status_col_all
    print(sca.loc['2024-02-01':'2024-02-06', cow])

    # raw inputs to compare against
    print("b_date:", obj.bd.loc[cow, 'b_date'], "| death:", obj.bd.loc[cow, 'death_date'])
    print("first calf:", obj.lb_pivot[1].get(cow))
    print(obj.MAB.fullday.loc['2024-02-01':'2024-02-06', cow])
    # position check
    print("pos in wy_ids:", list(obj.wy_ids).index(cow),
        "| pos in bd:", list(obj.bd.index).index(cow),
        "| pos in lb_pivot:", list(obj.lb_pivot.index).index(cow))

            
