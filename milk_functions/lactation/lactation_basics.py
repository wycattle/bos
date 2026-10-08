'''LactationBasics.py'''
import inspect
import pandas as pd
import numpy as np
from container import get_dependency

class LactationBasics:

    def __init__(self):
        print(f"LactationBasics instantiated by: {inspect.stack()[1].filename}") 


    def load(self):
        self.MB  = get_dependency('milk_basics')
        self.MAB = get_dependency('milk_aggregates_basic')  
        self.process()
        
    def process(self):
        [self.lactations_array, 
         self.headers] = self.create_lactation_basics()
        
        [self.ongoing_lactations, 
         self.last_lactations] = self.create_ongoing_lactations()
        
        

    def create_lactation_basics(self):
        ''' creates lactations from 2016-09-01'''
        milkx = self.MAB.fullday
        ext_range = self.MB.data['ext_rng']
        milk = milkx.reindex(ext_range)
        
        lastday = self.MB.data['lastday']

        lact_start2 = self.MB.data['start_pivot']        
        lact_stop2  = self.MB.data['stop_pivot']
        lact,  lactations = [],[]
        model = pd.DataFrame(index=range(0,999))
    
        WY_int = milkx.columns
        WY_str = [str(i) for i in WY_int]
        self.headers = WY_str
        self.lacts_str = [str(col) for col in lact_start2.columns]
        lacts_int = lact_start2.columns

        num_wy = len(WY_int)

        milk3 = model.copy()

        for i in lacts_int:
            lact = {}
            for j in WY_int:
                start = np.nan
                stop  = np.nan
                missing = False

                # If no start date -> no lactation
                if j not in lact_start2.index or i not in lact_start2.columns:
                    missing = True
                else:
                    start = lact_start2.loc[j, i]

                if pd.isna(start):
                    missing = True

                # If start exists, capture stop date; if it's missing, cow is still milking
                if not missing:
                    if (j in lact_stop2.index and i in lact_stop2.columns
                            and not pd.isna(lact_stop2.loc[j, i])):
                        stop = lact_stop2.loc[j, i]
                    else:
                        stop = lastday  # ongoing lactation

                if missing:
                    milk2 = model.copy()
                    milk2[''] = 0.0
                    milk2.name = j
                    milk3 = pd.concat([milk3, milk2], axis=1)
                    continue
                    
                milk1 = pd.DataFrame(milk.loc[start:stop, j])
                
                if not milk1.empty:
                    milk1 = milk1.reset_index(drop=True)

                    milk2 = model.merge(
                        milk1, left_index=True, right_index=True, 
                        how='left')
                    milk2 = milk2.fillna(0).infer_objects() #temp var so no copy is more efficient
                    
                else:
                    milk2 = model.copy()
                    milk2[0] = 0.0   # ensure one column placeholder
                    
                milk2.name = i

                milk3  = pd.concat([milk3, milk2], axis=1)
                milk2 = pd.Series()
                
            if milk3.shape[1] > 0:
                arr = np.array(milk3.fillna(0).infer_objects())
                if arr.ndim == 1:
                    arr = arr.reshape(-1, 1)
                # Target shape (1000, num_wy) – use 1000 rows (padded/truncated)
                # num_wy = len(WY_int)
                arr_target = np.zeros((1000, num_wy))
                rows = min(arr.shape[0], 1000)
                cols = min(arr.shape[1], num_wy)
                arr_target[:rows, :cols] = arr[:rows, :cols]
                arr = arr_target
                lact[i] = arr
                lactations.append(arr)

            #    reinitialize milk3
            milk3 = model.copy()
        
        self.lactations_array = np.dstack(lactations)#.transpose(1,2,0)

        
        print('lactations array',self.lactations_array.shape)
        return self.lactations_array, self.headers

    def create_ongoing_lactations(self):
        """For each WY id find:
           - ongoing: start date set, stop date missing (cow still milking)
           - last:    highest lactation number with any valid start date
        """
        start_pivot = self.MB.data['start_pivot']
        stop_pivot  = self.MB.data['stop_pivot']

        # Sort the column labels once, so we always walk 1 -> 6
        try:
            lact_cols = sorted(start_pivot.columns)
        except TypeError:
            lact_cols = list(start_pivot.columns)

        ongoing, last = {}, {}

        for wy in start_pivot.index:
            current = None
            latest  = None

            for lact in lact_cols:
                start = (start_pivot.loc[wy, lact]
                         if lact in start_pivot.columns else pd.NaT)
                if pd.isna(start):
                    continue

                latest = lact                     # keep overwriting -> ends as max

                stop = (stop_pivot.loc[wy, lact]
                        if lact in stop_pivot.columns else pd.NaT)
                if pd.isna(stop):
                    current = lact                # still open -> ongoing

            ongoing[wy] = current
            last[wy]    = latest

        self.ongoing_lactations = pd.Series(ongoing, dtype='object')
        self.last_lactations    = pd.Series(last,    dtype='object')
        
        return self.ongoing_lactations, self.last_lactations
        
        

if __name__ == "__main__":
    obj = LactationBasics()
    obj.load()    