'''milk_functions.lactations.this_lactation.py'''

import inspect
from container import get_dependency

class ThisLactation():
    def __init__(self):
        print(f"ThisLactation instantiated by: {inspect.stack()[1].filename}")

    def load(self):
        self.MB  = get_dependency('milk_basics')
        self.WD  = get_dependency('wet_dry')
        self.SD  = get_dependency('status_data')
        self.IUB = get_dependency('insem_ultra_basics')
        self.process()
        
    def process(self):
        
        self.milk           = self.MB.data['milk']
        self.last_calf_bdate= self.IUB.last_calf['last_calf_bdate']
        self.last_calf_num  = self.IUB.last_calf['last_calf_num']
        self.alive_ids      = self.SD .alive_ids_today_list

        
        #methods
        self.create_this_lactation_daily()
        

    def create_this_lactation_daily(self):
        pass

    

   
if __name__ == "__main__":
    obj = ThisLactation()
    obj.load()      