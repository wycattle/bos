'''milk_functions\\milk_aggregates.py

Second half of self.milk aggregation: halfday, tenday, monthly/weekly summaries.
Depends on milk_aggregates_basic (which provides fresh fullday and AM/PM matrices)
plus insem_ultra_data (for days-milking merge).
'''

import sys
import os
import inspect
import pandas as pd

from container import get_dependency


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class MilkAggregates:

    def __init__(self):
        print(f"MilkAggregates instantiated by: {inspect.stack()[1].filename}")
        
    def load(self):
        self.MAB  = get_dependency('milk_aggregates_basic')
        self.MB   = get_dependency('milk_basics')
        self.data = self.MB.data
        self.DR   = get_dependency('date_range')
        self.IUB  = get_dependency('insem_ultra_basics')
        self.IUD  = get_dependency('insem_ultra_data')
        self.process()

        
    def process(self):
        self.allx = self.IUD.allx
        
        # Pull computed results from MAB
        self.am               = self.MAB.am
        self.pm               = self.MAB.pm
        self.fullday          = self.MAB.fullday
        self.fullday.sort_index(inplace=True)
        self.fullday_lastdate = self.MAB.fullday_lastdate
        self.datex            = self.MAB.datex
        self.AM_liters        = self.MAB.AM_liters
        self.PM_liters        = self.MAB.PM_liters


        # methods
        startdate = self.DR.startdate  #timestamp
        self.start = pd.to_datetime(startdate)
        self.halfday = self.halfday_AM_PM()
        self.tenday, self.tenday1 = self.ten_day()

        [self.milk_sum, self.monthly_avg, self.monthly_total_by_cow,
                self.monthly_total,  self.monthly_avg,
                self.weekly_avg, self.weekly_total]                  = self.create_monthly_weekly()
       
    def halfday_AM_PM(self):
        lastday_AM = self.am.iloc[:,-1:]
        ldam=lastday_AM.loc[(lastday_AM.notna() ).any(axis=1),:].index.tolist()  
        
        lastday_PM = self.pm.iloc[:,-1:]
        ldpm=lastday_PM.loc[(lastday_PM.notna() ).any(axis=1),:].index.tolist() 
        
        halfday_AM = lastday_AM.loc[ldam,:]
        halfday_PM = lastday_PM.loc[ldpm,:]    
        
        self.halfday = halfday_AM.merge(halfday_PM, how='left', left_index=True, right_index=True)
        self.halfday.columns = ['AM', 'PM']
        self.halfday.index.name = 'wy_id'

        self.halfday = self.halfday.reset_index()
            
        return  self.halfday

    def ten_day(self):

        #get the last row of fullday and make list (milkers) of cols that are not NaN
        lastrow = self.fullday.iloc[-1:,:].copy()   
        milkers=lastrow.dropna(axis=1).columns.tolist()    
         # note that this drops cows from tenday that are gone on that last day
       
        self.tenday1 = self.fullday.iloc[-10:,:].copy() # has all wy's, datex index
        tenday2 = self.tenday1.loc[:,milkers]           # has milkers only
        
        tenday_cols1 = self.tenday1.index.to_list() #datex
        tenday_cols  = [date.strftime('%m-%d') for date in tenday_cols1]   #date headers for the 10 days of liters  
     
        tendayT=tenday2.T #date col headers
        tendayT.index.astype(int) #wy_ids
    
        tendayT.columns=tenday_cols  #dates
        avg = tendayT.mean(axis=1)
        tendayT['avg'] = avg
        lastcol = tendayT.iloc[:,9]  #10th col
        tendayT['pct chg from avg'] = ((lastcol/ tendayT['avg'] ) - 1)
  
        tendayT.index.name='wy_id'
        tenday3 = tendayT.reset_index()
        self.tenday = tenday3
        

        # self.tenday.to_excel("/home/alanw/Documents/tenday.xlsx")
        return self.tenday, self.tenday1
    
    def create_monthly_weekly(self):
        self.milk = self.fullday.loc[self.start:, :].copy()
        
        self.milk_sum = self.milk.sum(axis=1) # series with only the sum of the cols
        
        self.monthly_total_by_cow    = self.milk.resample('ME').mean()  # all the cows
        self.monthly_total  = self.milk_sum.resample('ME').sum()    # just the sum
        self.monthly_avg    = self.milk_sum.resample('ME').mean() 
        
        self.weekly_avg     = self.milk.resample('W').mean()
        self.weekly_total   = self.milk.resample('W').sum()
        return [self.milk_sum, self.monthly_avg, self.monthly_total_by_cow,
                self.monthly_total,  self.monthly_avg,
                self.weekly_avg, self.weekly_total]
        


if __name__ == '__main__':
    obj=MilkAggregates()
    obj.load()      