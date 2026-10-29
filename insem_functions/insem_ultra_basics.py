'''InsemUltraBasics.py'''
import inspect
import pandas as pd
import numpy as np
from container import get_dependency


tdy = pd.Timestamp.today()


class InsemUltraBasics:
    def __init__(self):

        print(f"InsemUltraBasics instantiated by: {inspect.stack()[1].filename}")

    def load(self):
        self.DR = get_dependency('date_range')
        self.MB = get_dependency('milk_basics')
        self.process()
        
    def process(self):
        self.data = self.MB.data

        self.df = pd.DataFrame()
        self.lbpiv = self.create_livebirths_pivot()
        self.first_calf = self.create_first_calf()
        self.last_calf  = self.create_last_calf()
        self.last_stop  = self.create_last_stop()
        self.write_to_csv()
        
        
    def create_livebirths_pivot(self):
        
        self.lbpiv = self.MB.data['start_pivot']
            
        return self.lbpiv
        
        
    
    def create_first_calf(self):
        
        first_calf1 = self.data['lb'].groupby('wy_id').agg({
            'b_date'  : 'min',
            'calf_num'   : 'min'
            }).reset_index()
        
        # self.first_calf = first_calf1.reindex(self.data['wy_ids'])
        # self.first_calf['wy_id'] = self.data['bd']['wy_id']     
           
        first_calf1.rename(columns={
            'calf_num': 'first calf_num',
            'b_date': 'first calf bdate'
            }, inplace=True)
        
        self.first_calf = first_calf1.set_index('wy_id')
        
        return self.first_calf

    

    def create_last_calf(self):
        
        last_calf1 = self.data['lb'].groupby('wy_id').agg({
            'b_date'  : 'max',
            'calf_num'   : 'max'
            }).reset_index()

        last_calf2 = last_calf1.rename(columns={
            'calf_num': 'last_calf_num',
            'b_date': 'last_calf_bdate'})
        
        last_calf2 = last_calf2.fillna(
            {'last_calf_num': 0})
        
        last_calf2['last_calf_age'] = (
            tdy - last_calf2['last_calf_bdate']).dt.days

        self.last_calf = last_calf2.set_index('wy_id')  # keep index for consistency
        
        return self.last_calf
    


    def create_last_stop(self):
        last_stop1 = self.data['stop'].groupby('wy_id').agg({
            'lact_num'    : 'max',
            'stop'        : 'max'
        })  .reset_index() 

        self.last_stop = last_stop1.reindex(self.data['wy_ids'])
        self.last_stop = self.last_stop.rename(columns = {'lact_num':'stop_calf_num','stop':'last_stop_date'})       
        self.last_stop = self.last_stop.fillna({'last_stop_date': np.nan})

        return self.last_stop
    
    def write_to_csv(self):
        pass
        # self.lbpiv.to_csv(r"E:\COWS\reports\\livebirths_piv.csv")


if __name__ == "__main__":
    obj=InsemUltraBasics()
    obj.load() 
    