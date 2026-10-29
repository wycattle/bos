'''finance_functions.PL.depreciation.py'''
import inspect
from pathlib import Path
import pandas as pd
from container import get_dependency

class DepreciationCalc:
    def __init__(self):
        print(f"DepreciationCalc instantiated by: {inspect.stack()[1].filename}")
        self.ptoc = None
        self.this_tax_year = 2025
        self.ptoc3 = None
        self.available_depr_summary = None
        self.available_depr_details = None

    def load_and_process(self):
        CP = get_dependency('capex_projects')
        self.ptoc = CP.ptoc.copy()
        self.ptoc3 = self.create_depreciation()
        self.available_depr_summary = self.create_tax_period()
        self.write_to_csv()
        
        
    def create_depreciation(self):
        ptoc1 = self.ptoc
        
        ptoc2 = ptoc1.drop(columns=(['materials','labor','sum']))
        
        ptoc2['equip %'] = .1
        ptoc2['bldg %'] = .05
        
        ptoc2['equip depr'] = ptoc2['equipment'] * ptoc2['equip %']
        ptoc2['bldg depr'] = ptoc2['bldg'] * ptoc2['bldg %']
        
        self.ptoc3 = ptoc2
        return self.ptoc3
    
    
    def create_tax_period(self):
        
        # maxyears_equip  = 10
        # maxyear_bldg    = 20
        taxyear1 = self.this_tax_year
        ptoc4 = self.ptoc3.copy()
        ptoc4['completion date'] = pd.to_datetime(ptoc4['completion date'])
        ptoc4['completion year'] = ptoc4['completion date'].dt.year
        
        years_left_to_depreciate =  taxyear1 - ptoc4['completion year']

        ptoc4['agg_depr_equip'] = ptoc4['equip depr'] * years_left_to_depreciate
        ptoc4['agg_depr_bldg']  = ptoc4['bldg depr']  * years_left_to_depreciate
 
        ptoc4['total depr'] = ptoc4['agg_depr_equip'] + ptoc4['agg_depr_bldg']
        
        ptoc5 = ptoc4[['project name','agg_depr_equip','agg_depr_bldg','total depr']]
        
        ptoc5.loc['Total'] = [
            "", 
            ptoc5['agg_depr_equip'].sum(), 
            ptoc5['agg_depr_bldg'].sum(), 
            ptoc5['total depr'].sum()
        ]

        
        self.available_depr_details = ptoc4
        self.available_depr_summary = ptoc5
        
        return self.available_depr_summary
    
    def write_to_csv(self):
        Path.home() / "cows_data" / "finance_data" / "capex" / "depreciation".mkdir(parents=True, exist_ok=True)
        self.available_depr_details.to_csv(Path.home() / "cows_data" / "finance_data" / "capex" / "depreciation" / 'available_depr_details.csv')
        self.available_depr_summary.to_csv(Path.home() / "cows_data" / "finance_data" / "capex" / "depreciation" / 'available_depr_summary.csv')
    
    
if __name__ == "__main__":
    obj=DepreciationCalc()
    obj.load_and_process()         