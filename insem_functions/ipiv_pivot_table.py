'''insem_functions/ipiv_pivot_table.py'''

import inspect
import pandas as pd
from   pipeline.neon.neon_connect import get_engine, read_sql_table_traced
from container import get_dependency


class IpivPivotTable:
    def __init__(self):
        print(f"ipiv_pivot_table instantiated by: {inspect.stack()[1].filename}")
        
        self.IUD = None
        self.ipiv_milkers =None
        self.ipiv_data = None
        self.ipiv_pivot_table = None
        self.pt=None
    
    def load(self):
         
        self.IUD = get_dependency('insem_ultra_data')
        self.IPIVD = get_dependency('ipiv_data')
        self.process()
        
    def process(self):
        
        self.ipiv_data = self.IPIVD.ipiv_data
        # engine = get_engine()
        # with engine.connect() as conn:
        #     self.ipiv_data = read_sql_table_traced('ipiv_data_formatted', conn)        
        
        #methods
        self.ipiv_pivot_table = self.create_ipiv_pivot_table()
        self.pt = self.join_cols_to_pivot()

    
    
    def create_ipiv_pivot_table(self):
        df_1 = self.ipiv_data
        self.pt = pd.pivot_table(df_1,
                            index= ['wy_id', 'lact_num'],
                            columns= 'try_num',
                            values= 'insem_date')
        return self.pt
        
    def join_cols_to_pivot(self):
        
        allxx = self.IUD.allx[['wy_id', 'u_read', 'days_milking']].copy()
        allxx = allxx.set_index('wy_id', drop=True)
        
        pt1 = self.pt.reset_index()
        
        self.ipiv_pivot_table = (
            pt1.merge(allxx, left_on='wy_id', right_index=True, how='left')
              .sort_values('wy_id')
              .reset_index(drop=True)
        )

        # self.ipiv_pivot_table = merge_1.reset_index().sort_values('wy_id').reset_index(drop=True)
        return self.ipiv_pivot_table
    

if __name__ == "__main__":
    obj=IpivPivotTable()
    obj.load()
        