'''milk_basics.py'''
import inspect
import pandas as pd
# from container import get_dependency
from utilities.db_retry import retry_db
from sqlalchemy import text
from   pipeline.neon.neon_connect import get_engine


class MilkBasics:
    @retry_db(max_retries=3, backoff_base=2)
    def __init__(self):
        print(f"MilkBasics instantiated by: {inspect.stack()[1].filename}")
        self.data = None
        self.lb = None
        self.u = None
        self.i = None
        self.bd = None
        self.lastday = None
        self.datex = None
        self.extended_date_range_milk = None
        self.wy_id_list = None
        self.start = None
        self.stop = None
        self.stop_pivot = None
        self.start_pivot = None


    def load_and_process(self):
        self.data = self.dataLoader()

    def dataLoader(self):
        engine = get_engine()
        with engine.connect() as conn:
            
            self.stop   = pd.read_sql(text("SELECT * FROM stop_dates"),   conn)
            self.lb     = pd.read_sql(text("SELECT * FROM live_births"),  conn)
            self.u      = pd.read_sql(text("SELECT * FROM ultra"),        conn)
            self.i      = pd.read_sql(text("SELECT * FROM insem"),        conn)
            self.bd     = pd.read_sql(text("SELECT * FROM birth_death"),  conn)
            # self.lb      = pd.read_sql(text("SELECT b_date FROM live_births"),  conn)
            
            self.lb     = self.lb   .drop(columns=['typex', 'readex', 'try_num'], errors='ignore')
            self.stop   = self.stop .drop(columns=['type'], errors='ignore')
            self.u      = self.u    .drop(columns=['type'], errors='ignore')
            self.i      = self.i    .drop(columns=['type'], errors='ignore')
            self.bd     = self.bd   .drop(columns=['type'], errors='ignore')
            

            # Get last date from am_wy view for lastday/datex
            am_wy = pd.read_sql(text('SELECT * FROM "AM_wy"'), conn)

        self.lastday = pd.to_datetime(am_wy['date'].iloc[-1], format='%Y-%m-%d', errors='coerce')
        self.datex   = pd.to_datetime(am_wy.columns    , format='%Y-%m-%d', errors='coerce')
        # Note:  'milk' is populated by MilkAggregatesBasic
        
        # date cols — self.lb / self.stop
        self.lb['b_date']   = pd.to_datetime(self.lb['b_date'], errors='coerce')
        self.lb = self.lb.sort_values(['wy_id'], ascending=True).reset_index(drop=True)
        
        self.stop['stop']   = pd.to_datetime(self.stop['stop_date'], errors='coerce')
        self.lb             = self.lb.fillna({'b_date': pd.NaT, 'calf_num': pd.NA})
        self.stop           = self.stop .fillna({'stop':   pd.NaT, 'calf_num': pd.NA})

        # date cols — self.bd
        self.bd['b_date']     = pd.to_datetime(self.bd['b_date'])
        self.bd['death_date'] = pd.to_datetime(self.bd['death_date'], errors='coerce')
        self.bd['arrived']    = pd.to_datetime(self.bd['arrived'],    errors='coerce')
        self.bd['adj_bdate']  = pd.to_datetime(self.bd['adj_bdate'],  errors='coerce')
        self.bd               = self.bd.sort_values('wy_id', ascending=True).reset_index(drop=True)

        # date cols — lb / u / i
        self.lb['b_date']    = pd.to_datetime(self.lb['b_date'],    errors='coerce')
        self.u['ultra_date'] = pd.to_datetime(self.u['ultra_date'], errors='coerce')
        self.u               = self.u.sort_values(['wy_id', 'calf_num', 'try_num']).reset_index(drop=True)
        
        self.i['insem_date'] = pd.to_datetime(self.i['insem_date'], errors='coerce')
        self.i               = self.i.sort_values(['wy_id', 'calf_num', 'try_num']).reset_index(drop=True)
        self.wy_id_list = self.bd['wy_id'].tolist()



        print('lastday:  ', self.lastday)
        self.bd    = self.bd

        start='2016-09-01'
        self.extended_date_range_milk = pd.date_range(
            start= start, end=self.lastday)

        start1 = self.lb[['wy_id', 'b_date', 'calf_num']].copy()
        self.start_pivot = pd.pivot_table( start1,
                                      index=    'wy_id',
                                      columns=  'calf_num',
                                      values=   'b_date',
                                      aggfunc=  'first'
                                      ).reindex(self.wy_id_list)
        
        stop1 = self.stop[['wy_id', 'stop_date', 'lact_num']].copy()
        self.stop_pivot = pd.pivot_table( stop1,
                                      index=    'wy_id',
                                      columns=  'lact_num',
                                      values=   'stop_date',
                                      aggfunc=  'first'
                                      ).reindex(self.wy_id_list)
        
        ultra1 = self.u[['wy_id', 'ultra_date', 'calf_num']].copy()
        self.ultra_pivot = pd.pivot_table( ultra1,
                                      index=    'wy_id',
                                      columns=  'calf_num',
                                      values=   'ultra_date',
                                      aggfunc=  'last'
                                      ).reindex(self.wy_id_list)



        self.data = {
            'datex'  : self.datex,
            'start'  : start,
            'stop'  : self.stop,
            'start_pivot' : self.start_pivot,
            'stop_pivot' : self.stop_pivot,
            'bd'     : self.bd,
            'lb'     : self.lb,
            'i'      : self.i,
            'u'      : self.u,
            'ultra_pivot': self.ultra_pivot,
            'lastday': self.lastday,
            'wy_ids' : self.wy_id_list,
            'ext_rng': self.extended_date_range_milk

        }
        return self.data


if __name__ == '__main__':
    mb = MilkBasics()
    mb.load_and_process()