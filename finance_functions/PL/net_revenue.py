'''finance_functions/PL/net_revenue.py'''
import inspect
import pandas as pd
import numpy as np
from pathlib import Path
from container import get_dependency


class NetRevenue:
    def __init__(self):
        print(f"NetRevenue instantiated by: {inspect.stack()[1].filename}")
        
    def load(self):
        self.MI   = get_dependency('milk_income')
        self.FW = get_dependency('feedcost_weekly')
        self.FB   = get_dependency('finance_basics')
        self.MA   = get_dependency('milk_aggregates')
        self.IUD  = get_dependency('insem_ultra_data')
        self.MB   = get_dependency('milk_basics')
        self.LB   = get_dependency('lactation_basics')
        
        self.process()

    def process(self):
        self.feedcost_total_weekly    = self.FW.feedcost_total_weekly
        self.feedcost_total_monthly   = self.FW.feedcost_total_monthly
        
        #startdate is one year ago
        self.startdate = (pd.Timestamp('now') - pd.DateOffset(years=1)).normalize()        
        
        
        self.birth_death = self.MB.data['bd'].copy()
        df = self.LB.last_lactations.to_frame(name='lact_num')
        df.index.name = 'wy_id'
        df = df.reset_index()          # columns: ['wy_id', 'lact_num']
        df['wy_id'] = df['wy_id'].astype(str)   # <-- match allx_cols dtype
        self.last_lact_num = df
        
        self.total_income_weekly  = self.MI.total_income_weekly.copy()
        self.total_income_monthly  = self.MI.total_income_monthly.copy()
        self.milk_income = self.MI.milk_income.copy()

        allx = self.IUD.allx.copy()
        self.allx_cols = allx[['wy_id','status','last_calf_num']].copy()
        self.allx_cols = self.allx_cols.reset_index(drop=True)
        self.allx_cols = self.allx_cols.rename(columns={'last_calf_num' : 'lact_num'})
        self.allx_cols['wy_id'] = self.allx_cols['wy_id'].astype(str)

        self.fullday_weekly_sum = self.LB.fullday_weekly_sum
            
        #methods
        self.total_net_revenue_weekly   = self.create_total_net_revenue_weekly()
        self.total_net_revenue_monthly  = self.create_total_net_revenue_monthly()

        


    
    # net-revenue weekly is total for all cows -- baht - not 'liters'
    def create_total_net_revenue_weekly(self):
        income1 = self.total_income_weekly.copy()
        cost1   = pd.DataFrame(self.feedcost_total_weekly.copy())

        # sliced to truncated_start_date already --- both income and cost are 1 col
        nr1 = income1.merge(cost1, how='left',
            left_index=True,
            right_index=True
            )

        nr1.columns = ['income', 'cost']    
        nr1['net_revenue'] = nr1['income'] - nr1['cost']

        self.total_net_revenue_weekly = nr1

        return self.total_net_revenue_weekly


    def create_total_net_revenue_monthly(self):
        weekly_df = self.total_net_revenue_weekly

        # Resample to monthly frequency and sum values
        self.total_net_revenue_monthly = weekly_df.resample('ME').sum()
        return self.total_net_revenue_monthly

    

   
    def write_to_csv(self):
        output_dir = Path("/home/alanw/Documents/vsCode_output/finance/net_revenue")
        output_dir.mkdir(parents=True, exist_ok=True)

        self.total_net_revenue_weekly        .to_csv(output_dir / "net_revenue_weekly.csv")
        self.total_net_revenue_monthly       .to_csv(output_dir / "net_revenue_monthly.csv")

if __name__ == "__main__":
    obj=NetRevenue()            
    obj.load()
    obj.write_to_csv() 