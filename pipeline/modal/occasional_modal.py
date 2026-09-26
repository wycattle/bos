'''pipeline/modal/occasional_modal.py'''

"""
This module is imported from two different places that run in two
different filesystems:

- the remote Modal function (run_modal_selector.py, inside the
  Modal container)
- main() (local, on your host machine)

Each of those callers is responsible for pushing the correct project
root onto sys.path BEFORE importing this module — /root/bos remotely,
BOS_ROOT locally. That's why there is no sys.path.insert(...) in this
file: hardcoding one path here would silently break the other caller.
If you ever see "ModuleNotFoundError: No module named 'container'"
coming from this file, the fix belongs in the CALLER, not here.
"""

import os
os.environ["BOS_LOCAL"] = "0"  # gets use

import pandas as pd
from container import get_dependency
from pipeline.neon.format_for_neon import FormatForNeon
from pipeline.neon.neon_connect import get_engine

class OccasionalModal:

    TABLE_NAMES = [
        "next_ultra_check", "i_u_merge",
        "allx", "ipiv_data",
        "feed_cost_pivot", "cost_xfeed_pivot",
        "ipiv_pivot_table", "net_revenue",
        "daily_milk_vs_fullday", "daily_milk_vs_fullday"
    ]

    @classmethod
    def select_targets(cls):
        """Local-only interactive picker. Import stays inside the method
        so remote containers never need questionary installed."""
        import questionary
        selected = questionary.checkbox(
            "Occasional — which tables changed?",
            choices=cls.TABLE_NAMES,
        ).ask()
        return selected or []

    def __init__(self, targets=None, branch="production"):
        self.branch = branch
        self.targets = set(targets) if targets else set(self.TABLE_NAMES)
        unknown = self.targets - set(self.TABLE_NAMES)
        if unknown:
            raise ValueError(f"Unknown targets: {unknown}")
        print(f"OccasionalModal targets: {sorted(self.targets)} (branch={self.branch})")

        self.nuc_fmt = FormatForNeon(schema={
            "ultra": "text", "group": "text", "wy_id": "int", "expected_bdate": "date",
        })
        self.ium_fmt = FormatForNeon(schema={"wy_id": "int"})
        self.allx_fmt = FormatForNeon(schema={
            "wy_id": "int", "status": "text", "last_stop_date": "date",
            "stop_calf_num": "int", "last_calf_bdate": "date", "last_calf_num": "int",
            "days_milking": "int", "i_calf_num": "int", "i_date": "date",
            "age_insem": "int", "u_calf_num": "int", "u_date": "date", "u_read": "text",
            "age_ultra": "int", "expected_bdate": "date", "exp_drydate": "date",
            "i_check": "int", "u_check1": "int", "u_check2": "int", "updated": "date",
        })
        self.ipiv_data_fmt = FormatForNeon(schema={
            "wy_id": "int", "lact_num": "int", "try_num": "int", "insem_date": "datex",
        })
        self.feed_cost_pivot_fmt = FormatForNeon(schema={
            "datex": "datex", "desc_2": "text", "value": "float",
        })
        self.cost_xfeed_pivot_fmt = FormatForNeon(schema={
            "datex": "datex", "desc_1": "text", "value": "float",
        })
        self.ipiv_pivot_table_fmt = FormatForNeon(
            schema={"wy_id": "int", "lact_num": "int", "u_read": "text", "days_milking": "int"},
            positional_rules=[(3, None, "date")],
        )
        self.net_revenue_table_fmt = FormatForNeon(
            schema={"datex": "date", "income": "float", "cost": "float", "net_revenue": "float"},
        )
        self.daily_milk_vs_fullday_fmt = FormatForNeon(schema={
            "datex": "datex", "am_liters": "float", "pm_liters": "float", "total_liters": "float",
        })

    def load_and_process(self):
        if "next_ultra_check" in self.targets:
            self.NUC = get_dependency('next_ultra_check')
        if "i_u_merge" in self.targets:
            self.IUM = get_dependency('i_u_merge')
        if "allx" in self.targets:
            self.IUD = get_dependency('insem_ultra_data')
        if "ipiv_data" in self.targets:
            self.IPIV = get_dependency('ipiv_data')
        if {"feed_cost_pivot", "cost_xfeed_pivot"} & self.targets:
            self.FB = get_dependency('finance_basics')
        if "ipiv_pivot_table" in self.targets:
            self.IPIVT = get_dependency('ipiv_pivot_table')
        if "net_revenue" in self.targets:
            self.NR = get_dependency('net_revenue')
        if "daily_milk_vs_fullday" in self.targets:
            self.DMVF = get_dependency('daily_milk_vs_fullday')

        self.createOccasionalData()
        self.write_to_neon(get_engine(branch=self.branch))

    def createOccasionalData(self):
        if "next_ultra_check" in self.targets:
            self.next_ultra_check_formatted = self.NUC.next_ultra_check.copy()
        if "i_u_merge" in self.targets:
            self.i_u_merge_formatted = self.IUM.iu.copy()
        if "allx" in self.targets:
            self.allx_formatted = self.IUD.allx.copy()
            self.allx_formatted['updated'] = pd.Timestamp.now()
        if "ipiv_data" in self.targets:
            self.ipiv_data_formatted = self.IPIV.ipiv_data.copy()
        if "feed_cost_pivot" in self.targets:
            self.feed_cost_pivot_formatted = self.FB.feed_cost_pivot.copy()
        if "cost_xfeed_pivot" in self.targets:
            self.cost_x_feed_formatted = self.FB.cost_xfeed_pivot_long.copy()
        if "ipiv_pivot_table" in self.targets:
            self.ipiv_pivot_table_formatted = self.IPIVT.ipiv_pivot_table.copy()
        if "net_revenue" in self.targets:
            nr = self.NR.net_revenue_monthly.copy()
            nr.index = nr.index.to_timestamp()
            nr.index.name = 'datex'
            self.net_revenue_table_formatted = nr.reset_index()
        if "daily_milk_vs_fullday" in self.targets:
            self.daily_milk_vs_fullday_formatted = self.DMVF.daily_milk_vs_fullday.copy()

    def write_to_neon(self, engine):
        with engine.begin() as conn:
            if "next_ultra_check" in self.targets:
                self.nuc_fmt.write_conn(self.next_ultra_check_formatted, 'next_ultra_check_formatted', conn, pk_col='wy_id')
            if "i_u_merge" in self.targets:
                self.ium_fmt.write_conn(self.i_u_merge_formatted, 'iu_merge_formatted', conn)
            if "allx" in self.targets:
                self.allx_fmt.write_conn(self.allx_formatted, 'allx_formatted', conn, pk_col='wy_id')
            if "ipiv_data" in self.targets:
                self.ipiv_data_fmt.write_conn(self.ipiv_data_formatted, 'ipiv_data_formatted', conn,
                    pk_col=['wy_id', 'lact_num', 'try_num'])
            if "feed_cost_pivot" in self.targets:
                self.feed_cost_pivot_fmt.write_conn(self.feed_cost_pivot_formatted, 'feed_cost_pivot_formatted', conn,
                    pk_col=['datex', 'desc_2'])
            if "cost_xfeed_pivot" in self.targets:
                self.cost_xfeed_pivot_fmt.write_conn(self.cost_x_feed_formatted, 'cost_x_feed_formatted', conn,
                    pk_col=['datex', 'desc_1'])
            if "ipiv_pivot_table" in self.targets:
                self.ipiv_pivot_table_fmt.write_conn(self.ipiv_pivot_table_formatted, 'ipiv_pivot_table_formatted', conn, pk_col='wy_id')
            if "net_revenue" in self.targets:
                self.net_revenue_table_fmt.write_conn(self.net_revenue_table_formatted, 'net_revenue_table_formatted', conn, pk_col='datex')
            if "daily_milk_vs_fullday" in self.targets:
                self.daily_milk_vs_fullday_fmt.write_conn(self.daily_milk_vs_fullday_formatted, 'daily_milk_vs_fullday_formatted', conn, pk_col='datex')