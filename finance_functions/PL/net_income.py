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
        
        self.net_revenue      = self.NR.net_revenue_monthly
        self.total_cost_xfeed = self.FB.total_cost_xfeed
        self.total_cost_xfeed.index = pd.to_datetime(self.total_cost_xfeed.index).to_period('M')
        self.total_cost_xfeed.index.name = 'datex'

        engine = get_engine()

        with engine.connect() as conn:
            self.cost_xfeed_pivot= read_sql_table_traced('cost_x_feed_formatted', conn)
            
        self.non_feed_cost_df = self.FB.non_feed_cost_df
            
        #methods
        self.net_income = self.create_net_income()
        
    def create_net_income(self):
        
        nr = self.net_revenue
     
        cost = self.total_cost_xfeed
               
        cost = cost.reset_index()
                 
        nr2 = pd.merge(nr, cost, how='outer', on='datex')
        nr2['net_income'] = nr2['net_revenue'] - nr2['total_xfeed_cost']
        nr2 = nr2.rename(columns={'cost': 'feed_cost'})
        
        nr2['liters_shortfall'] = (nr2['net_income'] / 22)/30
        nr2['liters_for_bkeven'] = -nr2['liters_shortfall'] + nr2['avg_liters']
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