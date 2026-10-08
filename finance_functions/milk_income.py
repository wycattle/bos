'''finance_functions/income/milk_income.py'''
import inspect
import pandas as pd

from container import get_dependency

tdy = pd.Timestamp('now').strftime('%Y-%m-%d %H_%M_%S')

class MilkIncome:
    def __init__(self):
        print(f"MilkIncome instantiated by: {inspect.stack()[1].filename}")

       
    def load(self):
        self.DR  = get_dependency('date_range')
        self.MA = get_dependency('milk_aggregates')
        self.process()
        
    def process(self):
        
        self.start = pd.Timestamp('2026-01-01')
        
        self.milk_daily         = self.MA.milk
        self.milk_weekly_total  = self.MA.weekly_total
        self.milk_monthly_total = self.MA.monthly_total
        self.milk_monthly_avg   = self.MA.monthly_avg
 
        self.income_daily       = self.create_income_daily()
        self.income_weekly      = self.create_income_weekly()
        self.income_monthly     = self.create_income_monthly()
        
    def create_income_daily(self):
        
                
        milk = self.milk_daily.copy()
        milk.index = pd.to_datetime(milk.index)
        milk = milk.sort_index()

        
        milk_liters = milk.loc[self.start:, :].copy()
        self.milk_liters_daily_sum = milk_liters.sum(axis=1)
        
        income = self.milk_liters_daily_sum * 22
        self.income_daily = pd.DataFrame(income)
        return self.income_daily
    
    
    def create_income_weekly(self):
        milk = self.milk_weekly_total.copy()
        milk_liters = milk.loc[self.start:, :].copy()
        
        milk_liters_weekly = milk_liters.sum(axis=1)
        
        income = milk_liters_weekly * 22
        self.income_weekly = pd.DataFrame(income)
        return self.income_weekly
    
    def create_income_monthly(self):
        
        milk = self.milk_monthly_total.copy()
        milk_liters_monthly = milk.loc[self.start:].copy()
        

        
        income = milk_liters_monthly * 22
        self.income_monthly = income.to_frame(name='income_monthly')     
        avg_liters    = self.milk_monthly_avg
        

        self.income_monthly = pd.concat([income.rename('income'), avg_liters.rename('avg_liters')], axis=1)
        return self.income_monthly

if __name__ == '__main__':
    obj=MilkIncome()
    obj.load()
    