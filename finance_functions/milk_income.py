'''finance_functions/income/milk_income.py'''
import inspect
import pandas as pd

from container import get_dependency

tdy = pd.Timestamp('now').strftime('%Y-%m-%d %H_%M_%S')

class MilkIncome:
    def __init__(self):
        print(f"MilkIncome instantiated by: {inspect.stack()[1].filename}")
        self.FCBD = None
        self.DR = None
        self.MA = None
        
        #methods
        self.startdate = None
        self.milk_weekly_total  = None
        self.milk_monthly_total = None
       
        self.income = None
        self.income_daily = None
        self.income_weekly = None
        self.income_monthly = None


    def load(self):
        self.DR  = get_dependency('date_range')
        self.MA = get_dependency('milk_aggregates')
        
        self.process()
        
    def process(self):
        

        self.startdate          = self.DR.startdate
        self.milk_daily         = self.MA.milk
        self.milk_weekly_total  = self.MA.weekly_total
        self.milk_monthly_total = self.MA.monthly_total
        self.milk_monthly_avg   = self.MA.monthly_avg
 
        self.income_daily       = self.create_income_daily()
        self.income_weekly      = self.create_income_weekly()
        self.income_monthly     = self.create_income_monthly()
        
    def create_income_daily(self):    
        income_1 = self.milk_daily.copy()
        income_2 = income_1 * 22
        self.income_daily = pd.DataFrame(income_2)
        return self.income_daily
    
    
    def create_income_weekly(self):
        income_1 = self.milk_weekly_total.copy()
        income_2 = income_1 * 22
        self.income_weekly = pd.DataFrame(income_2)
        return self.income_weekly
    
    def create_income_monthly(self):
        income = self.milk_monthly_total * 22
        self.income_monthly = income.to_frame(name='income_monthly')     
        avg_liters    = self.milk_monthly_avg
        

        self.income_monthly = pd.concat([income.rename('income'), avg_liters.rename('avg_liters')], axis=1)
        return self.income_monthly

if __name__ == '__main__':
    obj=MilkIncome()
    obj.load()
    