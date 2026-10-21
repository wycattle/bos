# milk_functions/forecast.py
import sys
import os
import inspect
import pandas as pd

from container import get_dependency


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class MilkForecast:

    def __init__(self):
        print(f"Forecast instantiated by: {inspect.stack()[1].filename}")
        
    def load(self):
        self.WL = get_dependency('weekly_lactations')

        self.process()

    def process(self):
        self.get_lactation_averages()

    def get_lactation_averages(self):
        lact_1 = self.WL
        




if __name__ == '__main__':
    obj=MilkForecast()
    obj.load()             