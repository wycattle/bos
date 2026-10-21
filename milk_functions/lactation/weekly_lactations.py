'''WeeklyLactations.py'''
import inspect
import pandas as pd
from pathlib import Path
from container import get_dependency


class WeeklyLactations():
    def __init__(self):
        print(f"WeeklyLactations instantiated by: {inspect.stack()[1].filename}")
   

    def load(self):
        self.MB     = get_dependency('milk_basics')
        self.DR     = get_dependency('date_range')
        self.L      = get_dependency('lactations')
        self.SD     = get_dependency('status_data')
        self.process()
        
    def process(self):

        self.data       = self.MB.data
        self.alive_ids  = [str(i) for i in self.SD.alive_ids_today_list]

        (self.lact1, self.lact2, 
         self.lact3, self.lact4, 
         self.lact5)    = self.create_308day()
        
        self.wk_lacts   = self.create_weekly()

        (self.lactation_wk_1, self.lactation_wk_2, 
         self.lactation_wk_3, self.lactation_wk_4, 
         self.lactation_wk_5) = self.create_separate_lactations()
        
        (self.max_liters, self.avg_liters, 
         self.sum_liters) = self.create_max_avg_sum_liters()
        
    
        self.create_live_lactations()
        self.write_to_csv()


    def create_308day(self):
        ''' limit the lactation to 308 days'''
        self.lact1 = self.L.L1.iloc[:308,:].copy()
        self.lact2 = self.L.L2.iloc[:308,:].copy()
        self.lact3 = self.L.L3.iloc[:308,:].copy()
        self.lact4 = self.L.L4.iloc[:308,:].copy()
        self.lact5 = self.L.L5.iloc[:308,:].copy()

        return (self.lact1, self.lact2, self.lact3,
                self.lact4, self.lact5    )
        


    def create_weekly(self):
        ''' convert the 308 day lacts to 44wks '''
        var = (self.lact1, self.lact2, self.lact3, self.lact4, self.lact5    )
        self.wk_lacts = []
        j = 0
        for i in var:   # i is the entire lact df

            grouping_key    = i.index // 7 # the //7 creates the 7 row grouping
            var2       = i.groupby(grouping_key).mean()
            var2.index = var2.index.astype(int)
            self.wk_lacts.append(var2)
            j +=1

        return self.wk_lacts # nested list

    def create_separate_lactations(self):
        ''' CONTAINS ALL COWS NOW LACTATING '''
        wl = self.wk_lacts

        self.lactation_wk_1 = wl[0]
        self.lactation_wk_2 = wl[1]
        self.lactation_wk_3 = wl[2]
        self.lactation_wk_4 = wl[3]
        self.lactation_wk_5 = wl[4]

        return     (self.lactation_wk_1,
                    self.lactation_wk_2,
                    self.lactation_wk_3,
                    self.lactation_wk_4,
                    self.lactation_wk_5
                    )
        
    def create_max_avg_sum_liters(self):
        
        lacts = (self.lactation_wk_1, self.lactation_wk_2,
                 self.lactation_wk_3, self.lactation_wk_4,
                 self.lactation_wk_5)
        
        lact_names = ['lact_1', 'lact_2', 'lact_3', 'lact_4', 'lact_5']
        
        self.max_liters = pd.DataFrame(
            [lact.max() for lact in lacts],
            index=[lact_names]
            )
        self.avg_liters = pd.DataFrame(
            [lact.mean() for lact in lacts],
            index=[lact_names]
            )
        self.sum_liters = pd.DataFrame(
            [lact.sum() for lact in lacts],
            index=[lact_names]
            )
                    

        return self.max_liters, self.avg_liters, self.sum_liters

    def create_live_lactations(self):
        #filter by alive_ids
        self.live_lact_wk_1 = self.lactation_wk_1.loc[:,self.alive_ids]
        self.live_lact_wk_2 = self.lactation_wk_2.loc[:,self.alive_ids]
        self.live_lact_wk_3 = self.lactation_wk_3.loc[:,self.alive_ids]
        self.live_lact_wk_4 = self.lactation_wk_4.loc[:,self.alive_ids]
        self.live_lact_wk_5 = self.lactation_wk_5.loc[:,self.alive_ids]
        
        return [self.live_lact_wk_1, self.live_lact_wk_2, self.live_lact_wk_3,
                self.live_lact_wk_4, self.live_lact_wk_5]
              
              

    def write_to_csv(self):
        output_dir = Path("/home/alanw/Documents/vsCode_output/milk")
        output_dir.mkdir(parents=True, exist_ok=True)        
        
        max_liters_df = pd.DataFrame(self.max_liters)
              
        max_liters_df.to_csv(output_dir / "max_liters.csv")
        self.avg_liters.to_csv(output_dir / "avg_liters.csv")
        self.sum_liters.to_csv(output_dir / "sum_liters.csv")

if __name__ == "__main__":
    obj = WeeklyLactations()
    obj.load()