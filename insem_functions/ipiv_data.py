import inspect
from pathlib import Path
import pandas as pd
from container import get_dependency

class IpivData:
    def __init__(self):
        print(f"IpivData instantiated by: {inspect.stack()[1].filename}")
        self.MB = None
        self.DR = None
        self.IUB = None
        self.IUD = None
        self.insem = None
        self.alive_ids = None
        self.ipiv_data = None
        self.ipiv_milkers = None

    def load(self):
        self.MB  = get_dependency('milk_basics')
        self.DR  = get_dependency('date_range')
        self.IUB = get_dependency('insem_ultra_basics')
        self.IUD = get_dependency('insem_ultra_data')
        self.process()
        
    def process(self):
        self.insem      = self.IUB.data['i']
        alive_ids1      = self.IUB.data['bd'].loc[self.IUB.data['bd']['death_date'].isnull()]
        alive_ids2      = alive_ids1.reset_index()
        self.alive_ids  = alive_ids2['wy_id']
        
        #methods
        self.ipiv_data  = self.create_this_calf()

  
    def create_this_calf(self):
        lc1 = self.IUB.last_calf.reset_index()
        lc2 = lc1[['wy_id', 'last_calf_num']].copy()
        # lc2['last_calf_num'] += 1
        lc = lc2.rename(columns={'last_calf_num' : 'lact_num'})
         
        # Filter with alive_ids
        this_calf_2 = lc[lc['wy_id'].isin(self.alive_ids)].reset_index(drop=True)
        
        insem1      = self.insem.copy()
        insem2      = insem1[insem1['wy_id'].isin ( self.alive_ids)].reset_index(drop=True)
        
        insem1['calf_num'] = insem1['calf_num'].fillna('0').astype(int)
        
        # this_calf_3 adds the try_nums to the 'last_calf' (now called 'lact_num)
        # and it gives us the date of the last insem...........
        this_calf_3 = this_calf_2.merge(insem2,
                                      left_on=['wy_id', 'lact_num'],
                                      right_on=['wy_id', 'calf_num'],
                                      how='right')

        this_calf_3 = this_calf_3.drop(columns=['lact_num','typex', 'readex'])
        
        max_calf = (
            this_calf_3.groupby('wy_id')['calf_num']
            .max()
            .rename('max_calf')
            .reset_index()
        )
            
            
        this_calf_4 = this_calf_3.merge(max_calf, on='wy_id', how='left')
        this_calf_4 = this_calf_4[this_calf_4['calf_num'] == this_calf_4['max_calf']].copy()  
        this_calf_4 = this_calf_4.rename(columns = {'calf_num' : 'lact_num' })
        this_calf_4 = this_calf_4.drop(columns='max_calf') 
        this_calf_5 = this_calf_4.reset_index(drop=True)                 
        
        self.ipiv_data = this_calf_5
        return self.ipiv_data
    


if __name__ == "__main__":
    obj=IpivData()
    obj.load()
    