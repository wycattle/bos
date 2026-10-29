''' milk_functions/lactation/milk_forecast.py '''
import sys
import os
import inspect
from pathlib import Path
import pandas as pd

from container import get_dependency


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class MilkForecast:

    def __init__(self):
        print(f"Forecast instantiated by: {inspect.stack()[1].filename}")
        
    def load(self):
        self.WL = get_dependency('weekly_lactations')
        self.MB = get_dependency('milk_basics')
        self.IUB = get_dependency('insem_ultra_basics')



        self.process()

    def process(self):

        self.BD = self.MB.data['bd'].copy()

        #methods
        self.forecast_set = self.create_forecast_set()
        

    def create_forecast_set(self):
        return self.forecast_set
        


    def write_to_csv(self):
        output_dir = Path("/home/alanw/Documents/vsCode_output/milk")
        output_dir.mkdir(parents=True, exist_ok=True)








        




if __name__ == '__main__':
    obj=MilkForecast()
    obj.load()
    obj.write_to_csv()             