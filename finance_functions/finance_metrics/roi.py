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
        self.HP     = get_dependency('heifer_price')
        self.MB     = get_dependency('milk_basics')
        self.NRBC   = get_dependency('net_revenue_by_cow')
        self.FCFC   = get_dependency('first_calf_feedcost')

        self.process()

    def process(self):
        self.startdate  = pd.Timestamp('2023-01-01')
        self.BD         = self.MB.data['bd'].copy()
        self.LB_pivot   = self.MB.data['live_birth_pivot']
        self.first_calf_feedcost = self.FCFC.first_calf_feedcost.copy()

        # methods

        self.bought_in_heifers  = self.create_bought_in_heifers()
        self.wy_born_heifers    = self.create_wy_born_heifers()
        self.herd               = self.create_herd()
        self.herd_cost          = self.create_herd_cost()
        self.herd_roi           = self.create_herd_roi()



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
        self.bought_in_heifers .rename(columns={ 1 : 'first_calf_bdate'}, inplace=True)
  

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
        self.wy_born_heifers.rename(columns={ 1 : 'first_calf_bdate'}, inplace=True)

        return  self.wy_born_heifers



    def create_herd(self):
        herd_1 = pd.concat([self.wy_born_heifers, self.bought_in_heifers],
                            axis=0).sort_values('wy_id').reset_index(drop=True)

        heifer_price = self.HP.heifer_price.copy()
        herd_2 = herd_1.merge(heifer_price,
                              how='left',
                              on='wy_id').reset_index(drop=True)
        self.herd = herd_2

        return self.herd

    def create_herd_cost(self):
        
        cost_df = self.first_calf_feedcost.copy()
  
        df2 = df1.merge(cost_df, on='wy_id', how='left')
        df2['cost_to_first_calf'] = (df2['feedcost_to_first_calf'].fillna(0) + df2['price'].fillna(0)).round()

        self.herd_cost = df2
        return self.herd_cost

    def create_herd_roi(self):
        CTFC = self.herd_cost.copy() 
        ctfc = CTFC[['wy_id','net revenue','months at WY','death_date','last_calf_num','net revenue/month','first_calf_bdate','feedcost_to_first_calf','price','cost_to_first_calf']]
        ctfc['revenue above cost'] = ctfc['net revenue'] - ctfc['cost_to_first_calf']
        ctfc = ctfc.sort_values('revenue above cost', ascending=False)

        ctfc2 = ctfc.loc[ctfc['death_date'].isna()].copy()
        self.herd_roi = ctfc2
        return self.herd_roi
    
    def write_to_csv(self):
        output_dir = Path("/home/alanw/Documents/vsCode_output/finance/investment/new_cows")
        output_dir.mkdir(parents=True, exist_ok=True)

        self.herd_cost.to_csv(output_dir / "herd_cost.csv", index=False)
        self.herd_roi.to_csv(output_dir /  "herd_roi.csv",  index=False)

if __name__=='__main__':
    obj = FinanceMetrics()
    obj.load()
    obj.write_to_csv()
        