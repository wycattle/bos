'''insem_ultra_data.py'''

from    datetime import datetime, timedelta
import  inspect
import  pandas  as pd
from pathlib import Path
from container import get_dependency

class InsemUltraData:
    def __init__(self):
        print(f"InsemUltraData instantiated by: {inspect.stack()[1].filename}")


    def load(self):
        # client = ContainerClient()
        self.DR     = get_dependency('date_range')
        self.MB     = get_dependency('milk_basics')
        self.SD     = get_dependency('status_data')
        self.IUB    = get_dependency('insem_ultra_basics')
        self.process()
        
    def process(self):
        self.data       = self.MB.data
        self.status_col = self.SD.status_col
        self.alive_mask = self.data['bd']['death_date'].isnull()
        self.date_format= '%m/%d/%Y'
        self.today      = pd.Timestamp(datetime.today())


        #methods
        self.last_insem         = self.create_last_insem()
        self.last_valid_insem   = self.create_last_valid_insem()
        self.last_invalid_insem = self.create_last_invalid_insem()
        self.last_ultra         = self.create_last_ultra()
        self.last_valid_ultra   = self.create_last_valid_ultra()
        self.last_invalid_ultra = self.create_last_invalid_ultra()
        self.df7                = self.create_df()
        
        (self.allx, self.all_milking, 
        self.all_dry, self.all_preg, 
        self.all_not_preg, self.days_milking) = self.create_allx()
        
        self.not_preg, self.no_insem = self.create_not_preg_df()
        
        self.write_to_csv()
        
        
    def create_last_insem(self):
        
        # get last insem event from 'i'
        i1 = self.data['i'].groupby('wy_id').last().reset_index()
        
        # print("i1 columns:", i1.columns.tolist())
        # print("i1 sample:\n", i1.head(2))
        i2 = i1.rename(columns = {
            'calf_num'    : 'i_calf_num',
            'insem_date'   : 'i_date',
            'try_num'      : 'try#'
            })
        
        # Convert to numeric, coerce errors to NaN
        i2['i_calf_num'] = pd.to_numeric(i2['i_calf_num'], errors='coerce')
        self.last_insem = i2.merge(self.IUB.last_calf, on='wy_id', how='left')
        return self.last_insem
  

    def create_last_valid_insem(self):
        # print("Shape of last_insem:", self.last_insem.shape)
        # print("Null i_calf_num count:", self.last_insem['i_calf_num'].isna().sum())
        # print("Null last_calf_num count:", self.last_insem['last_calf_num'].isna().sum())
        mask = (
            self.last_insem['i_calf_num'].isna() |
            (self.last_insem['i_calf_num'] > self.last_insem['last_calf_num'])
        )
        # print("Total True in mask:", mask.sum())
        i4 = self.last_insem.loc[mask].reset_index(drop=True)
        # print("i4 shape after filter:", i4.shape)
        self.last_valid_insem = i4[['wy_id','i_calf_num', 'i_date' ,'last_calf_num']]
        return self.last_valid_insem
    
    
    
    def create_last_invalid_insem(self):
        
        df = self.last_insem.loc[(
            self.last_insem['i_calf_num'] == self.last_insem['last_calf_num']
        )].reset_index(drop=True)
  
        self.last_invalid_insem = df[['wy_id','i_calf_num', 'i_date' ,'last_calf_num']]
        
        return self.last_invalid_insem



    def create_last_ultra(self):
        
        u1 = self.data['u'].groupby('wy_id').last().reset_index()
        self.last_ultra = u1.rename(columns = {'calf_num'  :'u_calf_num',
                            'ultra_date':'u_date',
                            'readex'    : 'u_read'
                            })
        
        return self.last_ultra
    
    
    def create_last_valid_ultra(self):
        
        df = self.last_valid_insem.merge(self.last_ultra,
                            on = "wy_id",
                            how = 'left'
                            )
        
        df1 = df.loc[(
            df['u_date'] > df['i_date']
            )
                          ].reset_index(drop=True)
        
        df2 = df1.drop(columns=(['i_calf_num','i_date','try_num', 'typex']))
               
        bdemask1 =  df2.loc[
            (df2 ['u_date'].notnull())  & 
            ((df2 ['u_read'] == 'ok' ) | (df2 ['u_read'] == 'x'))
            ]   
        
        bdemask = bdemask1 ['wy_id'].to_list()
                            
        valid_ultra1 = df2 [df2 ['wy_id'].isin(bdemask)].reset_index(drop=True)
        
        valid_ultra2 = valid_ultra1.merge(df[['wy_id', 'i_date']],
                             how = 'left',
                             on = 'wy_id'
                             )
        
        valid_ultra2['expected_bdate'] = pd.NaT 
        valid_ultra2.loc[
                valid_ultra2['u_read'] == ( 'ok'),'expected_bdate'
                ] = valid_ultra2['i_date'] + pd.to_timedelta(282, unit='D')
            
        valid_ultra2.loc[
                valid_ultra2['u_read'] == ( 'x'),'expected_bdate'
                ] = ''

   
        self.last_valid_ultra = valid_ultra2.drop(columns =  ['last_calf_num','i_date'])
        
        return self.last_valid_ultra
        
        
    def create_last_invalid_ultra(self):
        
        df = self.last_valid_insem.merge(self.last_ultra,
                            on = "wy_id",
                            how = 'left'
                            )
        
        df1 = df.loc[(
            df['u_date'] < df['i_date']     #note!  this is the Invalid ultra
            )
                          ].reset_index(drop=True)
        
        self.last_invalid_ultra = df1.drop(columns=(['i_calf_num','i_date','try_num', 'typex']))     
           
        return self.last_invalid_ultra        
        
        
    def create_df(self):
        
        #merge the valid and invalid dfs
        df3  = self.last_valid_insem .merge( right = self.last_valid_ultra,
                              how='left',
                              on='wy_id' )        
        
        last_calf_cols = self.IUB.last_calf[['last_calf_bdate', 'last_calf_age']]
        
        df3a = df3 . merge(
            last_calf_cols.reset_index(),
            on = 'wy_id',
            how='outer'
            )
        

        last_stop_cols = self.IUB.last_stop[['stop_calf_num','last_stop_date']]
        
        last_stop_cols.index.name = 'wy_id'
        df4 = df3a.merge(
            last_stop_cols.reset_index(),
            left_on='wy_id',
            right_index=True, 
            how='left' )  
        
        df4['age_insem'] =  (self.today - df4['i_date']).dt.days
        df4['age_ultra'] =  (self.today - df4['u_date']).dt.days
        df4['i_check']    = df4['i_calf_num'] - df4['last_calf_num']

        df4['u_check1']  =  df4['u_calf_num'] - df4['last_calf_num'] 
        df4['u_check2']  = (df4['u_date'] - df4['i_date']).dt.days
        
        df5 = df4.rename(columns={'last_calf_age': 'days_milking'}).reset_index(drop=True)
        # Convert status_col (DataFrame with dynamic column name) to wy_id, status format
        status_df = self.status_col.reset_index()
        status_df.columns=['wy_id','status']
        df5 = df5.merge(status_df, on='wy_id',how='left')

        df6 = df5[(df5['status'].notna()) & (df5['status'] != 'gone')].copy()
        df6['exp_drydate'] = df6['expected_bdate'] - timedelta(days=61)
        
        alive_ids = self.data['bd'].loc[self.alive_mask, 'wy_id']
        df7 = df6[df6['wy_id'].isin(alive_ids)].copy()
        df7 = df7.drop(columns='wy_id_x').reset_index(drop=True)
        self.df8 = df7
    
    def create_allx(self):
        
        self.allx = self.df8[
            [
            'wy_id',
            'status',
            'last_stop_date',
            'stop_calf_num',
            'last_calf_bdate',
            'last_calf_num',
            'days_milking',
            'i_calf_num',
            'i_date',
            'age_insem',
            'u_calf_num',
            'u_date',
            'u_read',
            'age_ultra',
            'expected_bdate',
            'exp_drydate',
            'i_check',
            'u_check1',
            'u_check2'
            # 'updated'
            ]
        ]
        
        self.all_milking = self.allx[self.allx['status'] == 'milking']
        self.all_dry     = self.allx[self.allx['status'] == 'dry']
        self.all_preg    = self.allx[self.allx['u_read'] == 'ok']
        self.all_not_preg = self.allx[ (self.allx['u_read'] != 'ok') ]
        self.days_milking = self.allx[['wy_id','days_milking']]
        
        return (self.allx, self.all_milking, 
                self.all_dry, self.all_preg, 
                self.all_not_preg, self.days_milking)
    

    def create_not_preg_df(self):
        notpreg1 = self.all_not_preg.loc[
            (
                (self.all_not_preg['age_insem'] >= 40)
            & (self.all_not_preg['age_insem'] .notnull())
            )
            |
            self.all_not_preg['i_date'] .isnull()
            
        ]



        notpreg2 = notpreg1[
            [
            'wy_id',
            'status',
            'days_milking',
            'i_calf_num',
            'i_date',
            'age_insem',
            'u_calf_num',
            'u_date',
            'u_read',
            'age_ultra',
            'u_check2'
            ]
        ]

        notpreg2 = notpreg2.rename(columns={'u_check2' : 'ultra-insem days'})
        notpreg2 = notpreg2.sort_values('ultra-insem days', ascending=False).reset_index(drop=True)

        notpreg3 = notpreg2.loc[(notpreg2['status'] == 'M')]
        self.not_preg = notpreg3

        self.no_insem = notpreg3.loc[
            notpreg3['i_date'] .isna()
        ].sort_values('days_milking', ascending=False).reset_index(drop=True)

        return self.not_preg, self.no_insem
    
    

    def write_to_csv(self):
        output_dir = Path("/home/alanw/Documents/vsCode_output/insem")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        self.allx    .to_csv(output_dir / "allx.csv")
        



if __name__ == "__main__":
    obj = InsemUltraData()
    obj.load()
    