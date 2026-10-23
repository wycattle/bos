''' finance_functions/PL/net_income.py '''
import inspect
import pandas as pd
from pathlib import Path
from container import get_dependency
from   pipeline.neon.neon_connect import get_engine, read_sql_table_traced

class NetIncome():
    def __init__(self):
        print(f"NetIncome instantiated by: {inspect.stack()[1].filename}")
        
    def load(self):
  
        self.NR = get_dependency('net_revenue')
        self.FB = get_dependency('finance_basics')

        self.process()
            
    def process(self):
        self.net_revenue = self.NR.total_net_revenue_monthly
        self.total_cost_xfeed = self.FB.total_cost_xfeed
        
        # Get data already processed in finance_basics
        self.cost_xfeed_pivot = self.FB.cost_xfeed_pivot_long
        self.non_feed_cost_df = self.FB.non_feed_cost_df
        
        # Convert indices to period[M] format
        self.total_cost_xfeed.index = pd.to_datetime(self.total_cost_xfeed.index).to_period('M')
        self.total_cost_xfeed.index.name = 'datex'
        
        # Trim to same date range as finance_basics
        start_date = self.FB.startdate
        self.net_revenue = self.net_revenue[self.net_revenue.index >= start_date]
        
        self.net_income = self.create_net_income()
            
    def create_net_income(self):
        nr = self.net_revenue.copy()
        nr.index = pd.to_datetime(nr.index).to_period('M')
        nr.index.name = 'datex'

        cost_xfeed = self.total_cost_xfeed.reset_index()
        cost_xfeed['datex'] = cost_xfeed['datex'].astype('period[M]')
        cost_xfeed = cost_xfeed.rename(columns={'total_xfeed_cost': 'cost_xfeed'})
    
        nr2 = pd.merge(nr, cost_xfeed, how='outer', on='datex')
        nr2['net_income'] = nr2['net_revenue'] - nr2['cost_xfeed']
        
        nr2['avg daily liters'] = (nr2['income'] / 22/30)
        nr2['shortfall, liters'] = -nr2['net_income'] /22/30
        nr2['liters needed for bkeven'] = nr2['shortfall, liters'] + nr2['avg daily liters']
        nr2['datex'] = pd.PeriodIndex(nr2['datex'], freq='M').to_timestamp()
        nr2 = nr2.sort_values('datex').reset_index(drop=True)
        
        self.net_income = nr2
        return self.net_income




    
    def write_to_csv(self):
        output_dir = Path("/home/alanw/Documents/vsCode_output/finance")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        self.net_income.to_csv(output_dir / "net_income.csv")   
        
        
if __name__ == "__main__":
    obj= NetIncome()
    obj.load()
    obj.write_to_csv()