'''pipeline/modal/daily_modal.py'''

import os
os.environ["BOS_LOCAL"] = "0"   
# Force this pipeline's DB target to Neon, unconditionally.
#
# neon_connect.get_engine() defaults to the local Docker mirror
# (BOS_LOCAL="1") unless told otherwise, and caches whichever engine
# it builds on first call for the life of the process. DailyModal's
# whole point is to compute fresh formatted tables and write them up
# to Neon — the one source of truth the bos_dashboard frontend reads
# from — so it must never read raw inputs from Docker, which is only
# ever a downstream mirror, refreshed *after* this script runs
# (see sync_neon_to_local.sh). Setting this before any get_dependency()
# call fires guarantees every engine built downstream — MilkBasics,
# MilkAggregates, WhiteboardGroups, etc. — points at Neon, regardless
# of what .env or the calling environment (local shell vs. Modal
# secret) may have set BOS_LOCAL to.
os.environ["BOS_LOCAL"] = "0"

import sys
from pathlib import Path
import inspect
# Add project root (bos_backend/) to sys.path so container module is found
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))


from pipeline.neon.format_for_neon import FormatForNeon


class DailyModal:
    def __init__(self):

        print(f"DailyModal instantiated by: {inspect.stack()[1].filename}")

        self.tenday = None
        self.halfday = None
        self.fullday = None
        self.WB_groups_tenday = None
        self.groups = None
        self.lactation_totals = None
        self.fullday_stats = None

        self.tenday_formatted = None
        self.halfday_formatted = None
        self.fullday_formatted = None
        self.WB_groups_formatted = None
        self.max_days_per_period_formatted = None
        self.lactation_totals_formatted = None
        self.fullday_stats_formatted = None


        # one FormatForNeon instance per table
        self.tenday_fmt = FormatForNeon(
            schema={
                "wy_id": "int",
                "avg": "float",
                "pct chg from avg": "percent",
            },
            positional_rules=[(1, 11, "int")],  # dynamic 10-day columns
        )
        self.halfday_fmt = FormatForNeon(
            schema={
                "wy_id": "int",
                "AM": "float",
                "PM": "float",
            },
            positional_rules=[(0, 1, "int")],  # the wy_id column, whatever it's named today
        )
        
        self.fullday_fmt = FormatForNeon()  # date-indexed, values left native float
        
        
        self.groups_fmt = FormatForNeon(
            schema={
                "wy_id" : "int",                
                "group_name": "text",
                "avg": "float",
                "days_milking": "int",
                "u_read": "text",
                "expected_bdate": "date",
                "snapshot_date": "date"
            },
            sort_by=[("group_name", "asc"),
                     ("avg", "desc")],
        )
        
        self.max_days_per_period_fmt = FormatForNeon(
            schema={ 
                "wy_id" : "int",
                "H"  : "int",	
                "W1" : "int",	
                "D1" : "int",	
                "W2" : "int",	
                "D2" : "int",	
                "W3" : "int",	
                "D3" : "int",	
                "W4" : "int",	
                "D4" : "int",	
                "W5" : "int",	
                "D5" : "int",	
                "W6" : "int",	
                "D6" : "int"
                }
            )
                
        self.lactation_totals_fmt = FormatForNeon(
            schema={
                "wy_id"     : "int",
                "l1_liters" : "float",
                "l2_liters" : "float",
                "l3_liters" : "float",
                "l4_liters" : "float",
                "l5_liters" : "float",
                "l6_liters" : "float",
                "total_liters"       : "float"
            }
        )
        
        self.fullday_stats_fmt = FormatForNeon(
            schema={
                "wy_id"  : "int",
                "liters" : "float",
                "count"  : "int",
                "avg"    : "float"
            }
        )
                    

    def load_and_process(self):
        
        from container import get_dependency
        self.MA = get_dependency('milk_aggregates')
        self.MAB= get_dependency('milk_aggregates_basic')
        self.WG = get_dependency('whiteboard_groups')
        self.WD = get_dependency('wet_dry')
        self.L  = get_dependency('lactations')
        

        #methods
        (self.tenday_formatted, self.halfday_formatted,
         self.fullday_formatted, self.WB_groups_formatted, 
         self.max_days_per_period_formatted,
         self.lactation_totals_formatted,
         self.fullday_stats_formatted )            = self.createDailyData()

        from   pipeline.neon.neon_connect import get_engine, read_sql_table_traced
        engine = get_engine()
        self.write_to_neon(engine)

    def write_to_neon(self, engine):
      
        with engine.begin() as conn:

            self.tenday_fmt.write_conn(
                self.tenday_formatted, 'tenday_formatted', conn, pk_col='wy_id')

            self.halfday_fmt.write_conn(
                self.halfday_formatted, 'halfday_formatted', conn)

            self.fullday_fmt.write_conn(
                self.fullday_formatted, 'fullday_formatted', conn, indexed_date=True)

            self.groups_fmt.write_conn(
                self.WB_groups_formatted, 'wb_groups_formatted', conn, pk_col='wy_id')
            
            self.max_days_per_period_fmt.write_conn(
                self.max_days_per_period_formatted, 'max_days_per_period_formatted', conn, pk_col='wy_id')
            
            self.lactation_totals_fmt.write_conn(
                self.lactation_totals_formatted, 'lactation_totals_formatted', conn, pk_col='wy_id')
            
            self.fullday_stats_fmt.write_conn(
                self.fullday_stats_formatted, 'fullday_stats_formatted', conn, pk_col='wy_id'
            )


    def createDailyData(self):
        """
        Pulls raw dependency dataframes and does ONLY the merge/slice logic
        specific to this report. No dtype coercion here — FormatForNeon
        handles that per-table in write_to_neon, at write time.
        """
        self.tenday  = self.MA.tenday.copy()
        self.halfday = self.MA.halfday.copy()
        self.fullday = self.MAB.fullday.copy()

        self.WB_groups_tenday    = self.WG.whiteboard_groups_tenday.copy()
        self.max_days_per_period = self.WD.max_days_per_period.copy()
        self.lactation_totals    = self.L.lactation_totals.copy()
        self.fullday_stats       = self.MAB.fullday_stats.copy() 
        

        return [self.tenday, self.halfday, self.fullday, 
                self.WB_groups_tenday, self.max_days_per_period,
                self.lactation_totals, self.fullday_stats 
                ]


if __name__ == "__main__":
    obj = DailyModal()
    obj.load_and_process()