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
        self.FCBD = get_dependency('feedcost_weekly')
        self.FB   = get_dependency('finance_basics')
        self.MA   = get_dependency('milk_aggregates')
        self.IUD  = get_dependency('insem_ultra_data')
        self.MB   = get_dependency('milk_basics')
        self.LB   = get_dependency('lactation_basics')
        
        self.process()

    def process(self):
        self.feedcost_weekly    = self.FCBD.feedcost_weekly
        self.feedcost_monthly  = self.FCBD.feedcost_monthly
        
        #startdate is one year ago
        self.startdate = (pd.Timestamp('now') - pd.DateOffset(years=1)).normalize()        
        
        
        self.birth_death = self.MB.data['bd'].copy()
        df = self.LB.last_lactations.to_frame(name='lact_num')
        df.index.name = 'wy_id'
        df = df.reset_index()          # columns: ['wy_id', 'lact_num']
        df['wy_id'] = df['wy_id'].astype(str)   # <-- match allx_cols dtype
        self.last_lact_num = df
        
        self.income_weekly  = self.MI.income_weekly.copy()
        self.income_monthly  = self.MI.income_monthly.copy()

        allx = self.IUD.allx.copy()
        self.allx_cols = allx[['wy_id','status','last_calf_num']].copy()
        self.allx_cols = self.allx_cols.reset_index(drop=True)
        self.allx_cols = self.allx_cols.rename(columns={'last_calf_num' : 'lact_num'})
        self.allx_cols['wy_id'] = self.allx_cols['wy_id'].astype(str)
            
        #methods
        self.adjusted_birth_death       = self.create_adjusted_birth_death()
        self.net_revenue_weekly         = self.create_net_revenue_weekly()
        self.net_revenue_sum   = self.create_net_revenue_sum()
        self.net_revenue_monthly        = self.create_net_revenue_monthly()

    
    
    
    
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
        
        self.adjusted_birth_death = bd
        return self.adjusted_birth_death
    
    
    # net-revenue weekly is for all cows -- only baht - no 'liters'
    def create_net_revenue_weekly(self):
        income1 = self.income_weekly.copy()
        cost1   = self.feedcost_weekly.copy()

        # slice to startdate
        income1 = income1.loc[income1.index >= self.startdate, :]
        cost1   = cost1.loc[cost1.index >= self.startdate, :]

        # income_weekly is a single aggregated column; feedcost_weekly is one column per wy_id
        income_series = income1.iloc[:, 0].rename('__income__')

        merged = cost1.join(income_series, how='left')

        cost_cols  = list(cost1.columns)
        net_revenue = (
            merged['__income__'].to_numpy()[:, None]
            - merged[cost_cols].to_numpy()
        )

        self.net_revenue_weekly = pd.DataFrame(
            net_revenue,
            index=merged.index,
            columns=cost_cols
        )

        return self.net_revenue_weekly


    def create_net_revenue_sum(self):
        nr1 = self.net_revenue_weekly
        nr2 = nr1.sum(axis=0)
        nr3 = nr2.to_frame(name='net_revenue')
        nr3.index.name = 'wy_id'
        nr3.index = nr3.index.astype(str)      # <-- match allx_cols dtype
        nr4 = nr3.reindex()
        
        nr5 = nr4.merge( self.allx_cols,
                how='left',
                left_on='wy_id',
                right_on='wy_id' 
                )
        
        bd_price = self.adjusted_birth_death[['wy_id', 'price']].copy()
        bd_price['wy_id'] = bd_price['wy_id'].astype(str)

        nr6 = nr5.merge(bd_price,
                how='left',
                on='wy_id'
                )
        
        nr6['adj_net_rev'] = nr6['net_revenue'] - nr6['price']
        
        nr7    = nr6.merge(self.last_lact_num,
                how='left',
                on='wy_id'
                )
        nr8 = nr7.loc[nr7['wy_id'].astype(int)>= 60, :]
        
        nr9 = nr8.sort_values('adj_net_rev', ascending=False)
        self.net_revenue_sum = nr9
        
        return self.net_revenue_sum
    
    
    

        #net-revenue monthly is the total of all cows in both baht + liters
    def create_net_revenue_monthly(self):
        
        IM = self.income_monthly
    
        income1 = IM.loc[ IM.index > self.startdate, :].copy()       #income monthly is already baht + liters
        
        cost1a  = pd.DataFrame(self.feedcost_monthly.sum(axis=1).rename('cost'))
        cost1   = cost1a.loc[cost1a.index > self.startdate, :].copy()
        
        # format as monthly period: 2025-06 instead of 2025-06-30
        # this eliminates the prob of one df being 2026-06-01 and the other 2026-06-30
        income1.index = pd.to_datetime(income1.index).to_period('M')
        cost1.index   = pd.to_datetime(cost1.index)  .to_period('M')
        
        cost1 = cost1.groupby(level=0).sum()
        cost1 = cost1.reindex(income1.index)
        income_1, cost_1 = income1, cost1

        net_revenue = income_1['income'] - (cost_1['cost']) 
        self.net_revenue_monthly = pd.DataFrame({
            'avg_liters':  income_1['avg_liters'],
            'income':      income_1['income'],
            'cost':        cost_1['cost'],
            'net_revenue': net_revenue            
        })
        return self.net_revenue_monthly

    def write_to_csv(self):
        output_dir = Path("/home/alanw/Documents/vsCode_output/finance")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        self.net_revenue_weekly .to_csv(output_dir / "net_revenue_weekly.csv")
        self.net_revenue_monthly.to_csv(output_dir / "net_revenue_monthly.csv")
        self.net_revenue_sum.to_csv(output_dir / "net_revenue_sum_all_cows.csv")
 
if __name__ == "__main__":
    obj=NetRevenue()            
    obj.load()
    obj.write_to_csv() 