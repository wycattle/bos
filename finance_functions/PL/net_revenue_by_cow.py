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
        self.total_feedcost_by_cow = self.FC.total_feedcost_by_cow   
        self.lactation_totals = self.Lact.lactation_totals        

        # DEBUG
        # print('lactation_totals:', type(self.lactation_totals), self.lactation_totals.shape)
        # print(self.lactation_totals.head())
        # print('feedcost:', type(self.total_feedcost_by_cow), self.total_feedcost_by_cow.shape)
        # print(self.total_feedcost_by_cow.head())


              
        #methods
        self.net_revenue_by_cow  =  self.create_net_revenue_by_cow()
        self.write_to_csv()

        
    def create_net_revenue_by_cow(self):
        income = (self.lactation_totals['sum'] * 22).to_frame('income')
        income.index = income.index.astype(str) 
        feedcost = (self.total_feedcost_by_cow).to_frame('feedcost')
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