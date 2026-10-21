'''finance_functions.income.IncomeStatement'''

import pandas as pd
from container import get_dependency
from pathlib import Path


class IncomeStatement:
    def __init__(self):
        self.NR = None
        self.Capex = None
        self.MI = None
        self.avg_liters = None
        self.net_income = None

    def load_and_process(self):
        self.NR = get_dependency('net_revenue')
        self.Capex = get_dependency('capex_basics')
        self.MI = get_dependency('milk_income')
        self.avg_liters = self.MI.total_income_monthly.loc[:, 'liters']
        self.net_income = self.createNetIncome()
        self.write_to_csv()
        
    def createNetIncome(self):
        inc1 = self.NR.net_revenue_monthly
        inc1['cost']    = self.Capex.non_capex_pivot['sum']
        inc1['net_income'] = inc1['net revenue'] - inc1['cost']
        inc2= pd.concat([inc1,self.avg_liters], axis=1)
        
        self.net_income = inc2
   
        return self.net_income


    def write_to_csv(self):
        Path.home() / "cows_data" / "finance_data" / "PL_data".mkdir(parents=True, exist_ok=True)
        self.net_income.to_csv(Path.home() / "cows_data" / "finance_data" / "PL_data" / 'net_income.csv')
        
        
if __name__ == "__main__":
    obj=IncomeStatement()
    obj.load_and_process()         
        