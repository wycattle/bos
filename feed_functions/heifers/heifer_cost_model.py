'''feed_functions/heifers/heifer_cost_model.py'''
from datetime import datetime
import pandas as pd
import numpy as np

from feed_functions.feedcost_basics import Feedcost_basics
from pathlib import Path

class HeiferCostModel:
    def __init__(self):

        self.FCB = Feedcost_basics()

    def load(self):
        
        self.milk_cost = 6 * 22
        
        now = datetime.now()
        self.today = pd.to_datetime(now)      
          
        start_date1 = pd.to_datetime('2024-10-20').date().isoformat()
        start_date2 = pd.to_datetime('2025-01-01').date().isoformat()

        # rng1 is for creating heifer 'days' 
        # rng2 is for the current accounting period

        self.rng1 = pd.date_range(start_date1, self.today, freq='D')    
        self.rng2 = pd.date_range(start_date2, self.today, freq='D')    

        self.milk_price = pd.Series(22.0)   # change this if the amount is changed
        self.milk_liters_day = pd.Series(6) # change this if the amount is changed

        self.kg_progression = pd.DataFrame(np.geomspace(6.0, 22.0, 180))
        
        # functions
        self.feed_price_df          = self.create_daily_feedprice()    
        self.heifer_feedcost_daily     = self.create_heifer_feedcost()
        
        [self.bd,
        self.heifer_days_range_dict, 
        self.milkdrinking_range_dict,
        self.eatingHeiferfood_range_dict, 
        self.eatingTMR_range_dict
        ]                           = self.create_feeding_ranges()
        self.feed_amount_kg            = self.create_feed_amount()
        self.heifer_feedcost_monthly = self.create_feedcost_monthly()
        
        self.write_to_csv()
        
        
        
        
    #uses the feed_series_dict - fsd -  from foodcostbasics to create a df 
    def create_daily_feedprice(self):
        
        fsd1 = self.FCB.feed_series_dict
        feed_type = self.FCB.feed_type
        
        psd_dict = {feed_type: v['psd'] for feed_type, v in fsd1.items() if 'psd' in v}
        
        feed_price_dict = {}
        for feed_type, df in psd_dict.items():
            # Assumes 'unit_price' column exists and index is date
            feed_price_dict[feed_type] = df['unit_price']

        # price/kg (columns=feed_type, index=date)
        self.feed_price_df = pd.DataFrame(feed_price_dict).reindex(self.rng2).ffill()

        return self.feed_price_df
    
    # this makes a timeseries - but amount still adds up to 1kg
    def create_heifer_feedcost(self):
        feed_csv_dir = Path.home() / "cows_data" / "feed_data" / 'feed_csv'
        diet1 = pd.read_csv(feed_csv_dir / 'heifer_daily_amt.csv')
        diet1['datex'] = pd.to_datetime(diet1['datex'], errors='coerce')
        diet1 = diet1.set_index('datex')
        diet2a = diet1.reindex(self.rng1).ffill()
        diet2  = diet2a.reindex(self.rng2).ffill()
        
        fpd = self.feed_price_df
        diet3 = pd.concat([diet2, fpd], axis=1)
        diet3['corn cost']      = diet3['corn kg']      * diet3['corn']
        diet3['cassava cost']   = diet3['cassava kg']   * diet3['cassava']
        diet3['beans cost']     = diet3['beans kg']     * diet3['beans']
        diet3['straw cost']     = diet3['straw kg']     * diet3['straw']
        diet3['bypass_fat cost']= diet3['bypass_fat kg']* diet3['bypass_fat']
        diet3['premix cost']    = diet3['premix kg']    * diet3['premix']
        diet3['baking soda cost']    = diet3['NaHCO3 kg'] * diet3['NaHCO3']
        diet3['total daily feedcost']= diet3.iloc[:,-7:].sum(axis=1)        
        
        # create diet/kg - here it is the same as diet3 - which is total 1kg in the csv
        heifer_feedcost = (diet3['total daily feedcost']) /  diet3['total kg']
        self.heifer_feedcost_daily = pd.DataFrame(heifer_feedcost, columns=['baht/day'])

        return self.heifer_feedcost_daily
       
        
    def create_feeding_ranges(self):
        # Use a CSV directory under Path.home() / "cows_data" / "feed_data" for heifers.csv
        csv_dir = Path.home() / "cows_data" / "feed_data".parent / 'csv_files'
        bd1 = pd.read_csv(csv_dir / 'heifers.csv')
        bd1['b_date']           = pd.to_datetime(bd1['b_date'], errors='coerce')
        bd1['adj_bdate']        = pd.to_datetime(bd1['adj_bdate'], errors='coerce')
        bd1['ultra_conf_date']  = pd.to_datetime(bd1['ultra_conf_date'], errors='coerce')        
        bd1['first_calf_bdate'] = pd.to_datetime(bd1['calf_bdate'], errors='coerce')


        # separate the heifers that are born here from the pregnant heifers brought in
        self.born_here_ids      = bd1.loc[(bd1['arrived'].isnull(), 'heifer_ids')].reset_index(drop=True) 
        self.born_elsewhere_ids = bd1.loc[(bd1['arrived'].notnull(), 'heifer_ids')].reset_index(drop=True) 

        self.bd = bd1.set_index( 'heifer_ids', drop=True)

        # Initialize all dicts before the loop
        self.heifer_days_range_dict = {}
        self.milkdrinking_range_dict = {}
        self.eatingHeiferfood_range_dict = {}
        self.eatingTMR_range_dict = {}
        self.preg_days_range_dict = {}
        
        for i in self.bd.index:
            
            date_born               = self.bd.loc[i,'b_date']
            date_preg               = self.bd.loc[i, 'ultra_conf_date']
            date_calf_bdate         = self.bd.loc[i, 'calf_bdate']  # the actual bdate, not the estimate. Set this after the birth just as a record
            date_stopMilkDrinking   = date_born + pd.Timedelta(days=75)
            date_startEatingHeiferFood = date_stopMilkDrinking + pd.Timedelta(days=1)
        
            

            # heifer timespan
            if pd.notna(date_born) and pd.isna(date_calf_bdate):
                heifer_days_range = pd.date_range(date_born, self.today)
            elif pd.notna(date_born) and pd.notna(date_calf_bdate):
                heifer_days_range = pd.date_range(date_born, date_calf_bdate)
            else:
                heifer_days_range = pd.DatetimeIndex([])
            self.heifer_days_range_dict[i] = heifer_days_range


            # milk drinking range
            if pd.notna(date_born) and pd.notna(date_stopMilkDrinking):
                milkdrinking_range = pd.date_range(date_born, date_stopMilkDrinking)
            else:
                milkdrinking_range = pd.DatetimeIndex([])
                
            self.milkdrinking_range_dict[i] = milkdrinking_range



            # eating heifer food range
            # if not yet pregnant            
            if pd.notna(date_startEatingHeiferFood) and pd.isna(date_preg):
                
                #do NOT use eatingHeiferfood_range = pd.date_range(date_startEatingHeiferFood, self.today)
                #that creates a separate date_range, this way adds the two params to the eatingHeiferfood_range tuple
                eatingHeiferfood_range = (date_startEatingHeiferFood, self.today)

                #if pregnant
            elif pd.notna(date_startEatingHeiferFood) and pd.notna(date_preg):
                eatingHeiferfood_range = (date_startEatingHeiferFood, date_preg - pd.Timedelta(days=1))
            else:
                eatingHeiferfood_range = (None, None)
                
            self.eatingHeiferfood_range_dict[i] = eatingHeiferfood_range


            # eating TMR range
                # if pregnant (but calf is not born yet - meaning the eating is'ongoing')
            if pd.notna(date_preg) and pd.isna(date_calf_bdate):
                eatingTMR_range = (date_preg, self.today)
                
                # is pregnant and calf is born
            elif pd.notna(date_preg) and pd.notna(date_calf_bdate):
                eatingTMR_range = (date_preg, date_calf_bdate)
            else:
                eatingTMR_range = (None, None)
            self.eatingTMR_range_dict[i] = eatingTMR_range
        
        
        
        return [self.bd, self.heifer_days_range_dict, self.milkdrinking_range_dict,
            self.eatingHeiferfood_range_dict, self.eatingTMR_range_dict ]
    
     
    
    
    def create_feed_amount(self):

        feed_amount_df = pd.DataFrame(index=self.rng1, columns=self.born_here_ids)
    
        for heifer_id in self.born_here_ids:
            
#milk drinking            
            #The get() method (for dict) returns  1)the specified key 2)the value of the item

            #initiation
            milk_dates = self.milkdrinking_range_dict.get(heifer_id, pd.DatetimeIndex([]))
            # assign 6 for all the dates in the milk drinking range
            feed_amount_df.loc[milk_dates, heifer_id] = 6


#heiferfood_range
            heiferfood_range = self.eatingHeiferfood_range_dict.get(heifer_id, (None, None))
            
            # heiferfood_range[0] is the startdate and heiferfood_range[1] is the stopdate
            if heiferfood_range[0] is not None and heiferfood_range[1] is not None:
                heiferfood_dates = pd.date_range(heiferfood_range[0], heiferfood_range[1])
                # Create a graduated Series for the heifer food phase
                n_days = len(heiferfood_dates)
                grad_series = np.geomspace(6.0, 30, 730)
                
                heiferfood_series = pd.Series(
                    grad_series[:n_days],
                    index=heiferfood_dates,
                    name='kg'
                )
                feed_amount_df.loc[heiferfood_dates, heifer_id] = heiferfood_series * self.heifer_feedcost_daily
                
                
                # heifer is past the milkdrinking 75 days, but is not preg, so heiferfood_range[1] = None (use today)
            elif heiferfood_range[0] is not None and heiferfood_range[1] is None:
                heiferfood_dates = pd.date_range(heiferfood_range[0], self.today)
                # Create a graduated Series for the heifer food phase
                n_days = len(heiferfood_dates)
                grad_series = np.geomspace(6.0, 30, 730)
                
                heiferfood_series = pd.Series(
                    grad_series[:n_days],
                    index=heiferfood_dates,
                    name='kg'
                )
                
                
                feed_amount_df.loc[heiferfood_dates, heifer_id] = heiferfood_series * self.heifer_feedcost_daily
                
                                
            elif heiferfood_range[0] is  None and heiferfood_range[1] is  None:
                pass
                
  
                
# 3. Eating adult TMR phase
            tmr_range = self.eatingTMR_range_dict.get(heifer_id, (None, None))
            TMR_amount_series =  self.FCB.current_feedcost.loc['sum','dry_kg']
            TMR_cost_series = self.FCB.current_feedcost.loc['sum','dry_cost']
            TMR_price_per_kg =TMR_cost_series / TMR_amount_series

            if tmr_range[0] is not None and tmr_range[1] is not None:
                tmr_dates = pd.date_range(tmr_range[0], tmr_range[1])
                tmr_cost  = TMR_price_per_kg  #float
                n_days = len(heiferfood_dates)
                grad_series = np.geomspace(6.0, 30, 730)
                
                TMR_amount_series = pd.Series(
                    grad_series[:n_days],
                    index=heiferfood_dates,
                    name='kg'
                )
                
            
                feed_amount_df.loc[tmr_dates, heifer_id] =  TMR_amount_series * tmr_cost



        feed_amount_df = feed_amount_df.fillna(np.nan)  # ensure NaN elsewhere
        self.feed_amount_kg = feed_amount_df
        
        return self.feed_amount_kg
    
    


        
        
    def create_feedcost_monthly(self):
        tfc1 = self.heifer_feedcost_daily
        tfc1['year']  = tfc1.index.year
        tfc1['month'] = tfc1.index.month
        
        tfc2 = tfc1.groupby(['year', 'month']).sum()
        tfc2 = tfc2.rename(columns={'baht/day': 'baht/month'})
        
        self.heifer_feedcost_monthly = tfc2
        
        return self.heifer_feedcost_monthly
    

        
    
    def write_to_csv(self):
        # Example: Save outputs to the Path.home() / "cows_data" / "feed_data" / 'heifers' directory
        heifers_dir = Path.home() / "cows_data" / "feed_data" / 'heifers'
        heifers_dir.mkdir(parents=True, exist_ok=True)
        # Uncomment to save outputs
        # self.heifer_feedcost_daily.to_csv(heifers_dir / 'heifer_cost_daily.csv')
        # self.heifer_feedcost_monthly.to_csv(heifers_dir / 'heifer_cost_monthly.csv')
        return
            
            
            
if __name__ == "__main__":
    obj = HeiferCostModel()
    obj.load()            
           