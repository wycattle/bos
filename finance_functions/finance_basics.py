'''finance_functions.FinanceBasics.py'''
import inspect
import pandas as pd
from   pathlib import Path
from   datetime import datetime, date
from container import get_dependency
from   pipeline.neon.neon_connect import get_engine, read_sql_table_traced

from feed_functions.feedcost_basics import FeedcostBasics


class FinanceBasics:
    def __init__(self, feedcost_basics=None):
        print(f"FinanceBasics instantiated by: {inspect.stack()[1].filename}")
    

    def load_and_process(self):

        self.startdate = pd.Timestamp('2025-10-01')
        
        self.engine = get_engine()            
        with self.engine.connect() as conn:
                    bkk = read_sql_table_traced('bkk_bank', conn)
        bkk = bkk.drop(columns=['id'])
                
        bkk['datex'] = pd.to_datetime(bkk['datex'])
        self.bkk_1 = bkk.loc[bkk['datex'] >= self.startdate, :].copy()
        
        self.bkk_farm_1 =self.bkk_1
                
        self.bkk_farm_1 = self.bkk_farm_1.drop(columns=['credit', 'desc_3', 'desc_4', 'brahman'])
        self.bkk_farm_1 = self.bkk_farm_1[
            self.bkk_farm_1['desc_1'].notna()].copy()  #removes the missing rows (when entry is in 'credit')
        
        self.bkk_farm_2 = self.bkk_farm_1[
            self.bkk_farm_1['desc_1'] !='nonfarm'].copy()  #bkk x nonfarm
        
        self.bkk_nonfarm = self.bkk_1[
            self.bkk_1['desc_1'] =='nonfarm'].copy()
        self.bkk_nonfarm = self.bkk_nonfarm.drop(columns=['credit', 'desc_4', 'brahman'])
                
        self.bkk_farm_non_capex = self.bkk_farm_2[
            self.bkk_farm_2['capex'] != 'x'].copy().drop(columns=['capex'])
        
        self.bkk_farm_capex = self.bkk_farm_2[
            self.bkk_farm_2['capex'] == 'x'].copy()        
        
        self.bkk_farm_x_feed = self.bkk_farm_non_capex[
            self.bkk_farm_non_capex['desc_1'] != 'feed' ].copy()
        
        self.bkk_feed = self.bkk_farm_non_capex[
            self.bkk_farm_non_capex['desc_1'] == 'feed' ].copy()

        #methods
        (self.feed_cost_df,
         self.feed_cost_pivot)      = self.create_feed_cost_pivot()
        
        (self.non_feed_cost_df, 
         self.cost_xfeed_pivot_long,
         self.total_cost_xfeed)     = self.create_cost_xfeed_pivot()
        
        self.nonfarm_df             = self.create_nonfarm_cost_df()
        self.write_to_csv()
        
        
        
    def create_feed_cost_pivot(self):
        df1 = self.bkk_feed.copy()
        df1['datex'] = pd.to_datetime(
            df1['year'].astype(str) + '-' + df1['month'].astype(str) + '-01'
        )
        df1 = df1.sort_values('datex')        
        
        df2 = pd.pivot_table(df1,
            index  = 'datex',
            values = 'debit',
            columns= 'desc_2',
            aggfunc= 'sum'  )
 
            # Melt wide pivot -> tidy long format
        self.feed_cost_pivot = (
            df2.stack()
            .rename('value')
            .reset_index()          # columns: datex, desc_2, value
            )
        self.feed_cost_df = df2
        return self.feed_cost_df, self.feed_cost_pivot
        
        
    def create_cost_xfeed_pivot(self):      # non-feed costs
        df = self.bkk_farm_x_feed.copy()
        df['datex'] = pd.to_datetime(
            df['year'].astype(str) + '-' + df['month'].astype(str) + '-01'
        )
        df = df[df['desc_1'] != 'sale']
        




        df2= (
            df.groupby(['datex', 'desc_1'], as_index=False)['debit']
            .sum()
            .rename(columns={'debit': 'value'})
        )       #longifies the cost data after grouping it by month (the datex line crams it together)

        
        df3 = pd.pivot_table(df2,
                index='datex',
                columns='desc_1',
                values='value',
                aggfunc='sum'
                )

        df3.index = df3.index.date
        
        df4 = df3.sum(axis=1)
        self.total_cost_xfeed = pd.DataFrame(df4, columns=['total_xfeed_cost'])
        
        
        self.cost_xfeed_pivot_long = df2       
        self.non_feed_cost_df = df3
        
        
        
        return self.non_feed_cost_df,self.cost_xfeed_pivot_long, self.total_cost_xfeed
     

    def create_nonfarm_cost_df(self):
        df1 = self.bkk_nonfarm
        df2 = df1.drop(columns=['capex', 'desc_1'])
        df2['desc_2'] = df2['desc_2'].fillna('misc')
        df2_pivot = pd.pivot_table(df2,
                index=['year','month'],
                columns='desc_2',
                values='debit',
                aggfunc='sum')
        
        self.nonfarm_df = df2_pivot
        return  self.nonfarm_df 
        
        
    def write_to_csv(self):
        
        output_dir = Path("/home/alanw/Documents/vsCode_output")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        self.feed_cost_df.to_csv(output_dir / "feed_cost_df.csv")
        self.non_feed_cost_df.to_csv(output_dir / 'non_feed_cost_df.csv')   
        self.nonfarm_df.to_csv  (output_dir / "self.nonfarm_df.csv")
        
        
        
if __name__ == "__main__":
    obj=FinanceBasics()
    obj.load_and_process() 