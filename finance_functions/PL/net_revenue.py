'''finance_functions\\PL\\net_revenue_daily.py'''
import inspect
import pandas as pd
import numpy as np
from pathlib import Path
from container import get_dependency


class NetRevenue:
    def __init__(self):
        print(f"NetRevenue instantiated by: {inspect.stack()[1].filename}")
        
    def load(self):
        self.MI   = get_dependency('milk_income')
        self.FW = get_dependency('feedcost_weekly')
        self.FB   = get_dependency('finance_basics')
        self.MA   = get_dependency('milk_aggregates')
        self.IUD  = get_dependency('insem_ultra_data')
        self.MB   = get_dependency('milk_basics')
        self.LB   = get_dependency('lactation_basics')

        
        self.process()

    def process(self):
        self.feedcost_total_weekly    = self.FW.feedcost_total_weekly
        self.feedcost_total_monthly   = self.FW.feedcost_total_monthly
        
        #startdate is one year ago
        self.startdate = (pd.Timestamp('now') - pd.DateOffset(years=1)).normalize()        
        
        
        self.birth_death = self.MB.data['bd'].copy()
        df = self.LB.last_lactations.to_frame(name='lact_num')
        df.index.name = 'wy_id'
        df = df.reset_index()          # columns: ['wy_id', 'lact_num']
        df['wy_id'] = df['wy_id'].astype(str)   # <-- match allx_cols dtype
        self.last_lact_num = df
        
        self.total_income_weekly  = self.MI.total_income_weekly.copy()
        self.total_income_monthly  = self.MI.total_income_monthly.copy()
        self.milk_income = self.MI.milk_income.copy()

        allx = self.IUD.allx.copy()
        self.allx_cols = allx[['wy_id','status','last_calf_num']].copy()
        self.allx_cols = self.allx_cols.reset_index(drop=True)
        self.allx_cols = self.allx_cols.rename(columns={'last_calf_num' : 'lact_num'})
        self.allx_cols['wy_id'] = self.allx_cols['wy_id'].astype(str)

        self.fullday_weekly_sum = self.LB.fullday_weekly_sum
            
        #methods
        self.heifer_price       = self.create_adjusted_birth_death()
        self.total_net_revenue_weekly   = self.create_total_net_revenue_weekly()
        self.total_net_revenue_monthly  = self.create_total_net_revenue_monthly()
        [self.avg_net_revenue_by_cow_weekly, 
         self.cumulative_avg_net_revenue_by_cow_weekly] = self.create_avg_net_revenue_by_cow_weekly()
        
        self.net_revenue_by_cow_by_week   = self.create_net_revenue_by_cow_by_week()



  
    def create_adjusted_birth_death(self):
        bd = self.birth_death.copy()
        dam_num = bd['dam_num']
        bd['price'] = pd.Series(
            np.select(
                [
                    dam_num == 'atom',
                    dam_num<1000,  #np.select picks the first matching condition, so dam_num < 1000 takes priority.
                    (dam_num > 1000) & (dam_num != 10000),
                    dam_num == 10000,
                ],
                [45000, 0, 65000, 45000],
                default=np.nan,
            ),
            index=bd.index,
        )
        
        self.heifer_price = bd[["wy_id","price"]]
        return self.heifer_price
    
    
    # net-revenue weekly is total for all cows -- baht - not 'liters'
    def create_total_net_revenue_weekly(self):
        income1 = self.total_income_weekly.copy()
        cost1   = pd.DataFrame(self.feedcost_total_weekly.copy())

        # sliced to truncated_start_date already --- both income and cost are 1 col
        nr1 = income1.merge(cost1, how='left',
            left_index=True,
            right_index=True
            )

        nr1.columns = ['income', 'cost']    
        nr1['net_revenue'] = nr1['income'] - nr1['cost']

        self.total_net_revenue_weekly = nr1

        return self.total_net_revenue_weekly


    def create_total_net_revenue_monthly(self):
        weekly_df = self.total_net_revenue_weekly

        # Resample to monthly frequency and sum values
        self.total_net_revenue_monthly = weekly_df.resample('ME').sum()
        return self.total_net_revenue_monthly


    def create_net_revenue_by_cow_by_week(self):

        cost1 = pd.DataFrame(self.FW.avg_feedcost_by_cow_weekly)
        # Assuming cost1 and milk_income are pandas DataFrames
        milk_income_reshaped = self.milk_income.reindex(index=cost1.index, columns=cost1.columns, fill_value=0)
        milk1 = milk_income_reshaped - cost1
        milk1.index.name = 'datex'
        milk2 = milk1


        print('cost1 shape= ', cost1.shape, 'milk2 shape=  ', milk2.shape)
        nr  = milk2 - cost1

        self.net_revenue_by_cow_by_week = nr
        
        return self.net_revenue_by_cow_by_week   
    

    def create_avg_net_revenue_by_cow_weekly(self):
                # Get feed cost (already vectorized in feedcost_weekly.py, shape: dates × cows)
        feed_cost = self.FW.avg_feedcost_by_cow_weekly

        # Compute net revenue per cow-week (vectorized subtraction)
        self.avg_net_revenue_by_cow_weekly = self.milk_income - feed_cost

        # Compute cumulative net revenue (vectorized cumsum along dates)
        self.cumulative_avg_net_revenue_by_cow_weekly = self.avg_net_revenue_by_cow_weekly.cumsum()

        return self.avg_net_revenue_by_cow_weekly, self.cumulative_avg_net_revenue_by_cow_weekly

    def write_to_csv(self):
        output_dir = Path("/home/alanw/Documents/vsCode_output/finance")
        output_dir.mkdir(parents=True, exist_ok=True)

        self.heifer_price                    .to_csv(output_dir / "heifer_price.csv")
        self.total_net_revenue_weekly        .to_csv(output_dir / "net_revenue_weekly.csv")
        self.total_net_revenue_monthly       .to_csv(output_dir / "net_revenue_monthly.csv")
        self.net_revenue_by_cow_by_week      .to_csv(output_dir / "net_revenue_by_cow_by_week.csv")

        self.cumulative_avg_net_revenue_by_cow_weekly    .to_csv(output_dir / "cumulative_avg_net_revenue_by_cow_weekly.csv")

if __name__ == "__main__":
    obj=NetRevenue()            
    obj.load()
    obj.write_to_csv() 