'''CreateStartDate.py'''

from datetime import datetime, timedelta
import pandas as pd
from container import get_dependency

class DateRange:
    def __init__(self):
        self.date_format = "ISO8601"
        self.startdate = None
        self.enddate_monthly = None
        self.enddate_daily = None
        self.date_range_daily = None
        self.date_range_weekly = None
        self.date_range_monthly1 = None
        self.date_range_monthly2 = None        

    def load_and_process(self):
        self.startdate          = self.start_date()
        self.enddate_daily      = self.end_date_daily()
        self.date_range_daily   = self.create_date_range_daily()
        self.date_range_weekly  = self.create_date_range_weekly()
        self.enddate_monthly    = self.end_date_monthly()
        [self.date_range_monthly1,
        self.date_range_monthly1]= self.create_date_range_monthly()
        
    def start_date(self):
        self.startdate = pd.to_datetime("2016-09-01")  #timestamp
        return self.startdate
    
    def end_date_monthly(self):

        today = datetime.now()
        first_day_of_current_month = today.replace(day=1)
        last_completed_month = first_day_of_current_month - timedelta(days=1)
        # first_day_of_last_completed_month = last_completed_month.replace(day=1)
        self.enddate_monthly = pd.to_datetime(last_completed_month)
        
        return  self.enddate_monthly
    
    def end_date_daily(self):
        # Get end date from milk_basics lastday (derived from live AM_wy sheet)
        MB = get_dependency('milk_basics')
        self.enddate_daily = MB.data['lastday']
        return self.enddate_daily
        
        
    def create_date_range_daily(self):
        self.date_range_daily = pd.date_range(start=self.startdate, 
                end=self.enddate_daily, freq='D')
        return self.date_range_daily
    
    def create_date_range_weekly(self):
        self.date_range_weekly = pd.date_range(start=self.startdate, 
                end=self.enddate_daily, freq='W')
        return self.date_range_weekly
    
    def create_date_range_monthly(self):
 
        start           = self.startdate
        end             = self.enddate_monthly
        drm = pd.date_range(start=start, end=end, freq='ME')

        year  = drm.year # ignore the squiggles
        month = drm.month
        day   = drm.days_in_month
        
        self.date_range_monthly1 = pd.MultiIndex.from_arrays([year, month], names=['year','month'])
        self.date_range_monthly2 = pd.MultiIndex.from_arrays([year, month, day], names=['year','month','days'])
        
        return  self.date_range_monthly1, self.date_range_monthly2
    

if __name__ == "__main__":
    obj = DateRange()
    obj.load_and_process()    
    