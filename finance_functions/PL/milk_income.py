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
        
        self.start = pd.Timestamp('2024-01-01')
        self.truncated_start    = self.DR.truncated_start_date

        self.milk_daily         = self.MA.milk

        self.milk_weekly_total  = self.MA.weekly_total
        self.weekly_total_by_cow= self.MA.weekly_total_by_cow
        self.milk_income        = self.weekly_total_by_cow * 22 # fullday liters => baht

        self.milk_monthly_total = self.MA.monthly_total
        self.milk_monthly_avg   = self.MA.monthly_avg
        self.milk_monthly_total_by_cow = self.MA.monthly_total_by_cow
 
        self.total_income_daily,    self.income_by_cow_daily      = self.create_income_daily()
        self.income_by_cow_weekly,  self.total_income_weekly      = self.create_income_weekly()
        self.income_by_cow_monthly, self.total_income_monthly     = self.create_income_monthly()
        
    def create_income_daily(self):
        
                
        milk = self.milk_daily.copy()
        milk.index = pd.to_datetime(milk.index)
        milk = milk.sort_index()

        
        milk_liters = milk.loc[self.truncated_start:, :].copy()
        self.milk_liters_daily_sum = milk_liters.sum(axis=1)
        
        total_income = self.milk_liters_daily_sum * 22   #series
        self.total_income_daily = pd.DataFrame(total_income)

 
        self.income_by_cow_daily = milk_liters * 22

        return self.total_income_daily, self.income_by_cow_daily
    
    
    def create_income_weekly(self):
        total_milk = self.milk_weekly_total.copy()
        total_milk_liters = total_milk.loc[self.truncated_start:, :].copy() #weekly milk (agg=sum) for all the cows, truncated
        total_milk_liters_weekly = total_milk_liters.sum(axis=1) #series --- the sum of all the cows
        
        total_income_weekly = total_milk_liters_weekly * 22
        self.income_by_cow_weekly = pd.DataFrame(total_milk_liters * 22)
        self.total_income_weekly = pd.DataFrame(total_income_weekly, columns=['income'])
        return self.income_by_cow_weekly, self.total_income_weekly
    
    def create_income_monthly(self):
        total_milk = pd.DataFrame(self.milk_monthly_total.copy())  
        total_milk_liters = total_milk.loc[self.truncated_start:, :].copy() #monthly milk (agg=sum) for all the cows, truncated
        total_milk_liters_monthly  = total_milk_liters.sum(axis=1) #series --- the sum of all the cows
        milk_liters_by_cow_monthly = total_milk_liters.copy()
        
        total_income_monthly = total_milk_liters_monthly * 22
        self.income_by_cow_monthly = pd.DataFrame(milk_liters_by_cow_monthly * 22)
        self.total_income_monthly = pd.DataFrame(total_income_monthly)
        return self.income_by_cow_monthly, self.total_income_monthly

    
if __name__ == '__main__':
    obj=MilkIncome()
    obj.load()
    