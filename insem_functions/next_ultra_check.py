"""
insem_functions\next_ultra_check.py
Class to create a DataFrame for next_ultra_check_dates.
Fields: wy_id, i_date, age_insem, next_ultra_check_date
Logic: If 'age_insem' is not null and 'u_date' is null, next_ultra_check_date = i_date + 40 days
Uses: get_dependency from container.py and allx from insem_ultra_data.py
"""

import pandas as pd
from pathlib import Path
from container import get_dependency


class NextUltraCheck:
    def __init__(self):
        # Only set up dependency, do not process data yet
        insem_ultra_data = get_dependency('insem_ultra_data')
        self.allx = insem_ultra_data.allx.copy()
        self.next_ultra_check = None

    def load(self):
        self.process()
        
    def process(self):

        # methods
        self.next_ultra_check = self._create_get_next_ultra_check()
        self.write_to_csv()
        

    def _create_get_next_ultra_check(self):
        # Filter rows where 'age_insem' is not null and 'u_date' is null

        mask = (
            self.allx['wy_id'].notnull()
            & self.allx['age_insem'].notnull()
            & self.allx['u_date'].isnull()
            & (self.allx['status'] == 'milking')
        )
        next_ultra_check = self.allx.loc[mask, ['wy_id', 'i_date', 'age_insem']].copy()
        # Calculate estimated ultra check date: i_date + 40 days
        # next_ultra_check['i_date'] = pd.to_datetime(next_ultra_check['i_date'], errors='coerce').dt.date
        next_ultra_check['next_ultra_check_date'] = next_ultra_check['i_date'] + pd.to_timedelta(40, unit='D')
            
        # Ensure column is datetime64 for sorting
        next_ultra_check['next_ultra_check_date'] = pd.to_datetime(next_ultra_check['next_ultra_check_date'], errors='coerce')
        next_ultra_check = next_ultra_check.loc[next_ultra_check['next_ultra_check_date'].sort_values(ascending=True).index].reset_index(drop=True)
        
        
        # Convert back to string date format for display
        next_ultra_check['i_date'] = next_ultra_check['i_date'].astype(str)
        next_ultra_check['next_ultra_check_date'] = next_ultra_check['next_ultra_check_date'].dt.date.astype(str)
        
        return next_ultra_check

    def get_next_ultra_check(self):
        return self.next_ultra_check


    def write_to_csv(self):
        output_dir = Path("/home/alanw/Documents/vsCode_output/insem")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        self.next_ultra_check    .to_csv(output_dir / "next_ultra_check.csv")


if __name__ == "__main__":
    obj = NextUltraCheck()
    obj.load()
