'''finance_functions/investment/new_cows/heifer_price.py'''
import inspect
import pandas as pd
import numpy as np
from pathlib import Path
from container import get_dependency


class HeiferPrice:
    def __init__(self):
        print(f"HeiferPrice instantiated by: {inspect.stack()[1].filename}")
        
    def load(self):
        # self.MI   = get_dependency('milk_income')
        # self.FW = get_dependency('feedcost_weekly')
        # self.FB   = get_dependency('finance_basics')
        # self.MA   = get_dependency('milk_aggregates')
        # self.IUD  = get_dependency('insem_ultra_data')
        self.MB   = get_dependency('milk_basics')
        self.LB   = get_dependency('lactation_basics')

        
        self.process()

    def process(self):

        #startdate is one year ago
        self.startdate = (pd.Timestamp('now') - pd.DateOffset(years=1)).normalize()        
        
        
        self.birth_death = self.MB.data['bd'].copy()
        df = self.LB.last_lactations.to_frame(name='lact_num')
        df.index.name = 'wy_id'
        df = df.reset_index()          # columns: ['wy_id', 'lact_num']
        df['wy_id'] = df['wy_id'].astype(str)   # <-- match allx_cols dtype
        self.last_lact_num = df
        
        #methods
        self.heifer_price       = self.create_heifer_price()

  
    def create_heifer_price(self):
        bd = self.birth_death.copy()
        dam_num = bd['dam_num']
        bd['price'] = pd.Series(
            np.select(
                [
                    dam_num == 'atom',
                    dam_num<1000,  #np.select picks the first matching condition, so dam_num < 1000 takes priority.
                    (dam_num > 1000) & (dam_num != 10000),
                    dam_num == 10000,
                ],
                [45000, 0, 65000, 45000],
                default=np.nan,
            ),
            index=bd.index,
        )
        
        self.heifer_price = bd[["wy_id","price"]]
        return self.heifer_price


    def write_to_csv(self):
        output_dir = Path("/home/alanw/Documents/vsCode_output/finance/investment/new_cows")
        output_dir.mkdir(parents=True, exist_ok=True)

        self.heifer_price.to_csv(output_dir / "heifer price.csv")

if __name__=="__main__":
    obj = HeiferPrice()
    obj.load()
    obj.write_to_csv()        