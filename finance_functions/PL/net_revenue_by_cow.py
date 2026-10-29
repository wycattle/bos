'''finance_functions/PL/net_revenue_by_cow.py'''
import inspect
import pandas as pd
import numpy as np
from pathlib import Path
from container import get_dependency

class NetRevenueByCow:
    def __init__(self):
        print(f"NetRevenueByCow instantiated by: {inspect.stack()[1].filename}")
        
    
    def load(self):
        self.FCW = get_dependency('feedcost_weekly')
        self.MI = get_dependency('milk_income')
        self.WL = get_dependency('weekly_lactations')
        self.MB = get_dependency('milk_basics')
        self.IUB= get_dependency('insem_ultra_basics')
        self.NR = get_dependency('net_revenue')
        self.HP = get_dependency('heifer_price')
        

        self.process()
             
    def process(self):

        self.BD = self.MB.data['bd'].copy()
                

        #methods
        self.net_revenue_by_cow_weekly = self.create_net_revenue_by_cow_weekly()
        self.net_revenue_by_cow_total = self.create_net_revenue_by_cow_total()
        
        [self.avg_net_revenue_by_cow_weekly, 
         self.cumulative_avg_net_revenue_by_cow_weekly] = self.create_avg_net_revenue_by_cow_weekly()
        
        self.net_revenue_analysis = self.create_net_revenue_analysis()



    def create_net_revenue_by_cow_weekly(self):
        feedcost = self.FCW.avg_feedcost_by_cow_weekly.copy()
        feedcost.index.name = 'datex'
        income   = self.MI.income_by_cow_weekly.copy()
        feedcost.index = feedcost.index.astype(str)
        income.index = income.index.astype(str)
        income = income.reindex(feedcost.index)
        nr1 = income - feedcost
        self.net_revenue_by_cow_weekly = nr1
        return self.net_revenue_by_cow_weekly


    def create_net_revenue_by_cow_total(self):
        nr1 = self.net_revenue_by_cow_weekly
        nrbc2 = nr1.sum(axis=0)
        nrbc2.index.name = 'wy_id'
        nrbc3 = pd.DataFrame(nrbc2, columns=['net revenue']).reset_index(drop=False)
        self.net_revenue_by_cow_total = nrbc3
        return self.net_revenue_by_cow_total


    def create_avg_net_revenue_by_cow_weekly(self):
                    # Get feed cost (already vectorized in feedcost_weekly.py, shape: dates × cows)
            feed_cost = self.FCW.avg_feedcost_by_cow_weekly
            milk_income = self.MI.milk_income

            # Compute net revenue per cow-week (vectorized subtraction)
            self.avg_net_revenue_by_cow_weekly = milk_income - feed_cost

            # Compute cumulative net revenue (vectorized cumsum along dates)
            self.cumulative_avg_net_revenue_by_cow_weekly = self.avg_net_revenue_by_cow_weekly.cumsum()

            return self.avg_net_revenue_by_cow_weekly, self.cumulative_avg_net_revenue_by_cow_weekly


    

    def create_net_revenue_analysis(self):
            
            cutoff_date = pd.Timestamp('2023-01-15')
            bd = self.BD # birth_death df
            net_revenue = self.net_revenue_by_cow_total.copy().round(0)
    
    
            arrived_after = bd.loc[bd['arrived'] >= cutoff_date].reset_index(drop=True)
            arrived_after_id_list = arrived_after['wy_id'].to_list()
         
            dead_now = arrived_after[arrived_after['death_date'].notnull()].reset_index(drop=True)
            last_calf1 = self.IUB.last_calf.copy()
            last_calf2  = pd.DataFrame(last_calf1, columns=['last_calf_num', 'last_calf_bdate'])
            last_calf  = last_calf2.reset_index(drop=False)
    
            df1 = arrived_after.merge(last_calf, 
                                     how='left',
                                     on='wy_id'
                                     )
            df2 = df1.drop(columns=['b_date', 'typex', 'readex'])
    
            df3 = df2.merge(net_revenue,
                            how='left',
                            on='wy_id').reset_index(drop=True)


            # Calculate months at WY with an explicit if-else logic
            arrived = pd.to_datetime(df3['arrived'])
            death   = pd.to_datetime(df3['death_date'])
            now     = pd.Timestamp.now()

            df3["months at WY"] = np.where(
                death.notna(),
                (death - arrived).dt.days / 30.4375,
                (now - arrived).dt.days / 30.4375
            ).round(0)

            df3['net revenue / month'] = (df3['net revenue'] / df3['months at WY']).round(0)

            self.net_revenue_analysis = df3
            return self.net_revenue_analysis



    def write_to_csv(self):
        output_dir = Path("/home/alanw/Documents/vsCode_output/finance/net_revenue/net_revenue_by_cow")
        output_dir.mkdir(parents=True, exist_ok=True)

        self.net_revenue_by_cow_weekly      .to_csv(output_dir / "net_revenue_by_cow_weekly.csv", index=False)
        self.net_revenue_by_cow_total       .to_csv(output_dir / "net_revenue_by_cow_total.csv", index=False)
        self.avg_net_revenue_by_cow_weekly  .to_csv(output_dir / "avg_net_revenue_by_cow_weekly.csv", index=True )
        self.cumulative_avg_net_revenue_by_cow_weekly.to_csv(output_dir / "cumulative_avg_net_revenue_by_cow_weekly.csv", index=True)

        self.net_revenue_analysis           .to_csv(output_dir / 'net_revenue_analysis.csv',     index=False)
        
        
if __name__ == "__main__":
    obj = NetRevenueByCow()
    obj.load()
    obj.write_to_csv()