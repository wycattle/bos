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
        self.MI = get_dependency('milk_income')

        self.process()
             
    def process(self):

        #methods
        self.total_net_revenue_weekly  =  self.create_total_net_revenue_weekly_weekly()
        self.net_revenue_by_cow_weekly = self.create_net_revenue_by_cow_weekly()
        self.write_to_csv()

        
    def create_total_net_revenue_weekly_weekly(self):
        income = self.MI.total_income_weekly.copy()  #df
        income.index = income.index.astype(str) 
        feedcost = pd.DataFrame(self.FC.feedcost_total_weekly.copy(), columns=['feedcost'])
        feedcost.index = feedcost.index.astype(str)
        nr1 = pd.merge(feedcost, income, left_index=True, right_index=True)
        nr1['net revenue'] = nr1['income'] - nr1['feedcost']
        
        self.total_net_revenue_weekly = nr1
        return self.total_net_revenue_weekly


    def create_net_revenue_by_cow_weekly(self):
        feedcost = self.FC.avg_feedcost_by_cow_weekly.copy()
        feedcost.index.name = 'datex'
        income   = self.MI.income_by_cow_weekly.copy()
        feedcost.index = feedcost.index.astype(str)
        income.index = income.index.astype(str)
        income = income.reindex(feedcost.index)


        nr1 = income - feedcost
        self.net_revenue_by_cow_weekly = nr1
        return self.net_revenue_by_cow_weekly



    def write_to_csv(self):
        output_dir = Path("/home/alanw/Documents/vsCode_output/finance")
        output_dir.mkdir(parents=True, exist_ok=True)
        self.total_net_revenue_weekly.to_csv(output_dir / "total_net_revenue_weekly.csv" )
        
        
        
if __name__ == "__main__":
    obj = NetRevenueByCow()
    obj.load()