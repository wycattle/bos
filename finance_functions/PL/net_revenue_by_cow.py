'''finance_functions/PL/net_revenue_by_cow.py'''
import inspect
import pandas as pd
from pathlib import Path
from container import get_dependency

class NetRevenueByCow:
    def __init__(self):
        print(f"NetRevenueByCow instantiated by: {inspect.stack()[1].filename}")
        
    
    def load(self):
        self.FC = get_dependency('feedcost_weekly')
        self.Lact = get_dependency('lactations')

        self.process()
             
    def process(self):
        self.total_feedcost_by_cow = self.FC.feedcost_weekly  #all cows 
        self.lactation_totals_all = self.Lact.lactation_totals_all        

        #methods
        self.net_revenue_by_cow  =  self.create_net_revenue_by_cow()
        self.write_to_csv()

        
    def create_net_revenue_by_cow(self):
        income = (self.lactation_totals_all['total_liters'] * 22).to_frame('income')
        income.index = income.index.astype(str) 
        feedcost = (self.total_feedcost_by_cow)
        feedcost.index = feedcost.index.astype(str)
        nr1 = pd.merge(feedcost, income, left_index=True, right_index=True)
        nr1['net revenue'] = nr1['income'] - nr1['feedcost']
        
        self.net_revenue_by_cow = nr1
        return self.net_revenue_by_cow
        
    def write_to_csv(self):
        output_dir = Path("/home/alanw/Documents/vsCode_output/finance")
        output_dir.mkdir(parents=True, exist_ok=True)
        self.net_revenue_by_cow.to_csv(output_dir / "net_revenue_by_cow.csv" )
        
        
        
if __name__ == "__main__":
    obj = NetRevenueByCow()
    obj.load()