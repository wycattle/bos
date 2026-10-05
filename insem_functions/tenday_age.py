import inspect
from pathlib import Path
import pandas as pd 

from container import get_dependency

class TendayMilkingDays:
    def __init__(self):
        print(f"TendayMilkingDays instantiated by: {inspect.stack()[1].filename}")
        self.IUD = None
        self.MA = None
        self.days = None
        self.preg = None
        self.td2 = None

    def load(self):
        self.IUD = get_dependency('insem_ultra_data')
        self.MA  = get_dependency('milk_aggregates')
        
        self.write_to_csv()
        self.process()
        
    def process(self):
        self.days= self.IUD.allx.loc[:, ['wy_id', 'days_milking']]
        self.preg= self.IUD.allx.loc[:, ['wy_id', 'u_read', 'expected_bdate']]
        self.td2 = self.tenday_days()

    def tenday_days(self):
        td = self.MA.tenday.reset_index()
        self.td2 = pd.merge(td, self.preg, on='wy_id', how='left')
        return self.td2

    def write_to_csv(self):
        output_dir = Path("/home/alanw/Documents/vsCode_output/insem")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        self.td2.to_csv( output_dir / self.tenday_days.csv)
        
if __name__ ==     "__main__"    :
    obj = TendayMilkingDays()
    obj.load()      
