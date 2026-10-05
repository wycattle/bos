'''feed_functions/heifers/heifers.py'''
import  inspect
from    datetime import datetime, timedelta
import  pandas as pd
import  numpy as np
from    container import get_dependency
from    sqlalchemy import text
from    pipeline.neon.neon_connect import get_engine

#This class is for heifers born/raised here --- bought from outside are treated in wet_dry

class Heifers:
    def __init__(self):
        print(f"Heifers instantiated by: {inspect.stack()[1].filename}")
        self.engine = get_engine()
        
        self.dry_feed_cost = None
        self.heifers = None
        self.heifer_ids_list = None
        self.heifer_days = None
        self.milk_drinking_days = None
        self.cost_milk = None



    def load(self):

        self.today = pd.Timestamp.today().normalize()    
        
        with self.engine.connect() as conn:
            self.heifers = pd.read_sql_table('heifers', conn)
            self.feed_daily_cost_by_group   = pd.read_sql_table('feed_daily_cost_by_group', conn)
            self.dry_feed_cost    = pd.DataFrame(self.feed_daily_cost_by_group['dry_cost']).sum(axis=0)
            self.heifer_feed_cost = pd.DataFrame(self.feed_daily_cost_by_group['heifer_cost']).sum(axis=0)

        self.process()
        
    def process(self):    

        self.rng =  pd.date_range(start='2024-01-01', end=self.today, freq='D' )
            
        # Methods
        self.heifers = self.create_heifer_df()
        self.heifer_days = self.create_heifer_days()

        [self.milk_drinking_days,
         self.cost_milk] = self.calc_milkdrinking_days()

        self.calc_heifer_feed_days()
        self.align_days()
        
        
    
    def create_heifer_df(self):
        
        heifers1 = self.heifers
        heifers1['b_date']              = pd.to_datetime(heifers1['b_date'])
        heifers1['actual_calf_bdate']   = pd.to_datetime(heifers1['actual_calf_bdate'])
        heifers1['est_calf_bdate']      = pd.to_datetime(heifers1['est_calf_bdate'])  
        heifers1['arrived']             = pd.to_datetime(heifers1['arrived'])                
        heifers1['gone_date']           = pd.to_datetime(heifers1['gone_date'])
        
        heifers1['age_days'] = (self.today - heifers1['b_date']).dt.days

        heifers1.reset_index()
        self.eartag_ids = heifers1['eartag_id'].astype(str)
        
        self.heifers = heifers1
                 
        return self.heifers
    

    def create_heifer_days(self):
        heif  = self.heifers.set_index('eartag_id')
        bdate = heif['b_date']

        # (m x 1) dates minus (1 x n) birthdates -> (m x n) ages in days
        dates_col    = self.rng.values[:, np.newaxis]     # (m, 1)
        birthdates_r = bdate.values[np.newaxis, :]        # (1, n)
        age_days = (dates_col - birthdates_r).astype('timedelta64[D]').astype(int) + 1  # birth date = day 1

        df = pd.DataFrame(age_days, index=self.rng, columns=bdate.index)

        dates = df.index.values[:, np.newaxis]            # (m, 1)

        # lower bound: nothing before birth  (kills the negative days)
        mask_lower = dates >= bdate.values[np.newaxis, :]

        # upper bound: earlier of gone_date / actual_calf_bdate (NaT = still active, no bound)
        # the .min(axis=1) at the end grabs the lessor of the two - so there is only one col left
        upper      = pd.concat([heif['gone_date'], heif['actual_calf_bdate']], axis=1).min(axis=1)
        has_upper  = upper.notna().values[np.newaxis, :]
        
        upper_v    = upper.values[np.newaxis, :]
        mask_upper = (~has_upper) | (dates <= upper_v)

        self.heifer_days = df.where(mask_lower & mask_upper)
        return self.heifer_days
        
    
    def calc_milkdrinking_days(self):
        
        days = self.heifer_days
        # 'milk' where the heifer is 90 days old or younger, blank otherwise
        milk = pd.DataFrame(
            np.where(days <= 90, 'milk', None),
            index=days.index,
            columns=days.columns,
        )

        self.milk_drinking_days = milk
        self.cost_milk = None  # set cost here when ready
        return milk, self.cost_milk


    
    def calc_heifer_feed_days(self):
        
        days = self.heifer_days

        # 'HFeed' where the heifer is older than the milk-drinking window (> 90 days)
        hfeed = pd.DataFrame(
            np.where(days > 90, 'HFeed', None),
            index=days.index,
            columns=days.columns,
        )

        # leave a column for cost (filled later from feed_daily_cost_by_group['heifer_cost'])
        hfeed['cost'] = None

        self.heifer_feed_days = hfeed
        return hfeed

 
     
    def align_days(self):
        
        new_index = pd.DataFrame()
        
        wy = self.heifer_ids_list
        heif1 = self.heifers
        heif1 = heif1.set_index('heifer_ids_list', drop=True)
        age = heif1['age_days']
        
        for i in wy:
            age1 = age[i]
            age_range = pd.RangeIndex(1,age1)
            
            milk_days1 = self.milk_drinking_days.loc[0,i]
            milk_index = pd.RangeIndex(1, milk_days1, name=i)
            milk_amt = 6
            milk_days1 = pd.Series(milk_amt, index=milk_index)
            milk_days = milk_days1.reindex(age_range, fill_value=0)


            
        
        return
            
     
if __name__ == "__main__":
    obj = Heifers()
    obj.load()    