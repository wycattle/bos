'''finance_functions/finance_metrics/roi.py'''
import inspect
import pandas as pd
import numpy as np
from pathlib import Path
from container import get_dependency

class FinanceMetrics:
    def __init__(self):
        print(f"FinanceMetrics instantiated by: {inspect.stack()[1].filename}")

    def load(self):
        self.HP = get_dependency('heifer_price')
        self.MB = get_dependency('milk_basics')

        self.process()

    def process(self):
        self.startdate = pd.Timestamp('2024-01-01')
        self.BD = self.MB.data['bd'].copy()
        self.LB_pivot = self.MB.data['live_birth_pivot']

        # methods

        self.bought_in_heifers  = self.create_bought_in_heifers()
        self.wy_born_heifers    = self.create_wy_born_heifers()
        self.herd               = self.create_herd_cost()



    def create_bought_in_heifers(self):

        bd = self.BD.copy()
        lbpivot = self.LB_pivot.copy().reset_index(drop=False)
        bought_in_heifers_1 = bd.loc[(bd['typex'] == 'buy'), :]  # df

        bought_in_heifers_list = bought_in_heifers_1['wy_id'].to_list()
        
        bought_in_heifers_df = pd.DataFrame(bought_in_heifers_list, columns=['wy_id'])

        bought_in_heifers_3 = bought_in_heifers_df.merge(lbpivot,
            how='left',
            on='wy_id'
        ).reset_index(drop=True)     

        #this returns a df that shows the bdate of calf1 (or NAT)
        self.bought_in_heifers = bought_in_heifers_3[['wy_id',1]]
        self.bought_in_heifers .rename(columns={ 1 : 'first calf bdate'}, inplace=True)
  

        return self.bought_in_heifers


    def create_wy_born_heifers(self):

        bd = self.BD.copy()
        lbpivot = self.LB_pivot.copy().reset_index(drop=False)
        wy_born = bd.loc[bd['typex'] == 'wy_born' , :]  # df

        wy_born_list = wy_born['wy_id'].to_list()
        
        wy_heifers_1 = pd.DataFrame(wy_born_list, columns=['wy_id'])

        wy_heifers_2 = wy_heifers_1.merge(lbpivot,
            how='left',
            on='wy_id'
        ).reset_index(drop=True)

        #this returns a df that shows the bdate of calf1 (or NAT)
        self.wy_born_heifers = wy_heifers_2[['wy_id',1]]
        self.wy_born_heifers.rename(columns={ 1 : 'first calf bdate'}, inplace=True)

        return  self.wy_born_heifers



    def create_herd_cost(self):
        herd_1 = pd.concat([self.wy_born_heifers, self.bought_in_heifers],
                            axis=0).sort_values('wy_id').reset_index(drop=True)

        heifer_price = self.HP.heifer_price.copy()
        herd_2 = herd_1.merge(heifer_price,
                              how='left',
                              on='wy_id').reset_index(drop=True)
        self.herd_cost = herd_2

        return self.herd_cost
    
    def write_to_csv(self):
        output_dir = Path("/home/alanw/Documents/vsCode_output/finance/investment/new_cows")
        output_dir.mkdir(parents=True, exist_ok=True)

        self.wy_born_heifers.to_csv(output_dir / "wy_born_heifers.csv", index=False)


if __name__=='__main__':
    obj = FinanceMetrics()
    obj.load()
    obj.write_to_csv()
        