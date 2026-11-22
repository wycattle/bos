'''feed_functions/first_calf_feedcost.py'''

import inspect
import pandas as pd
import numpy as np
# from pathlib import Path
from container import get_dependency

class FirstCalfFeedCost:
    def __init__(self):
        print(f"FirstCalfFeedCost instantiated by: {inspect.stack()[1].filename}")

    def load(self):
        # self.HP = get_dependency('heifer_price')
        self.MB   = get_dependency('milk_basics')
        self.NRBC = get_dependency('net_revenue_by_cow')
        self.FW   = get_dependency('feedcost_data')
        self.process()

    def process(self):
        self.startdate = pd.Timestamp('2023-01-01')
        self.BD = self.MB.data['bd'].copy()
        self.LB_pivot = self.MB.data['live_birth_pivot']

        #methods        
        self.first_calf_feedcost = self.create_first_calf_feedcost()



    def create_first_calf_feedcost(self):

        # cum avg feedcost cols are wyid and dates are the index - flip to slice
        feedcost_data_T = self.FW.cumulative_avg_feedcost_by_cow_weekly.T.loc[227:,:].copy()
        feedcost_data   = feedcost_data_T.T


        b_date = self.LB_pivot.loc[227:, 1 ].copy().to_frame()
        b_date.columns = ['first_calf_bdate']
        b_date = b_date.reset_index(drop=False)



        # Remove any accidental whitespace in column names
        b_date.columns = b_date.columns.str.strip()
        b_date['first_calf_bdate'] = pd.to_datetime(b_date['first_calf_bdate'])

        rows = []

        for wy_id, first_calf_bdate in zip(b_date['wy_id'], b_date['first_calf_bdate']):
            wy_id = int(wy_id)

            #check for blank values
            if pd.isna(first_calf_bdate):
                rows.append({
                    'wy_id': wy_id,
                    'first_calf_feedcost': np.nan
                })
                continue

            # Sum all weekly feedcost rows up to and including first_calf_bdate
            feedcost = feedcost_data.loc[: first_calf_bdate, wy_id].sum().round(0)

            rows.append({
                'wy_id': wy_id,
                'first_calf_feedcost': feedcost
            })

        cost_df = pd.DataFrame(rows)
        print('first_calf_feedcost: ', cost_df)

        self.first_calf_feedcost = cost_df
        return self.first_calf_feedcost



if __name__== "__main__":
    obj=FirstCalfFeedCost()
    obj.load()