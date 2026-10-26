'''pipeline/modal/daily_modal.py'''

"""
Imported from two places that run in different filesystems:
the remote Modal function (run_modal_selector.py) and main() locally.
Each caller pushes the correct project root onto sys.path BEFORE
importing this module, so there is no sys.path.insert here.
"""

from container import get_dependency
from pipeline.neon.format_for_neon import FormatForNeon
from pipeline.neon.neon_connect import get_engine


class DailyModal:

    TABLE_NAMES = [
        "tenday",
        "halfday",
        "fullday",
        "wb_groups",
        "max_days_per_period",
        "lactation_totals_live",
        "fullday_stats",
        "daily_milk_vs_fullday",
    ]

    @classmethod
    def select_targets(cls):
        """Local-only interactive picker."""
        import questionary
        selected = questionary.checkbox(
            "Daily — which tables to refresh?",
            choices=cls.TABLE_NAMES,
        ).ask()
        return selected or []

    def __init__(self, targets=None, branch="production"):
        self.branch = branch
        self.targets = set(targets) if targets else set(self.TABLE_NAMES)
        unknown = self.targets - set(self.TABLE_NAMES)
        if unknown:
            raise ValueError(f"Unknown targets: {unknown}")
        print(f"DailyModal targets: {sorted(self.targets)} (branch={self.branch})")

        self.tenday_fmt = FormatForNeon(
            schema={"wy_id": "int", "avg": "float", "pct chg from avg": "percent"},
            positional_rules=[(1, 11, "int")],  # dynamic 10-day columns
        )
        self.halfday_fmt = FormatForNeon(
            schema={"wy_id": "int", "AM": "float", "PM": "float"},
            positional_rules=[(0, 1, "int")],   # wy_id column, whatever it's named today
        )
        self.fullday_fmt = FormatForNeon()      # date-indexed, values left native float
        self.groups_fmt = FormatForNeon(
            schema={
                "wy_id": "int", "group_name": "text", "avg": "float",
                "days_milking": "int", "u_read": "text",
                "expected_bdate": "date", "snapshot_date": "date",
            },
            sort_by=[("group_name", "asc"), ("avg", "desc")],
        )
        self.max_days_per_period_fmt = FormatForNeon(schema={
            "wy_id": "int", "H": "int",
            "W1": "int", "D1": "int", "W2": "int", "D2": "int",
            "W3": "int", "D3": "int", "W4": "int", "D4": "int",
            "W5": "int", "D5": "int", "W6": "int", "D6": "int",
            "total": "int", "wet_pct": "float",
        })
        self.lactation_totals_live_fmt = FormatForNeon(schema={
            "wy_id": "int",
            "l1_liters": "float", "l2_liters": "float", "l3_liters": "float",
            "l4_liters": "float", "l5_liters": "float", "l6_liters": "float",
            "total_liters": "float",
        })
        self.fullday_stats_fmt = FormatForNeon(schema={
            "wy_id": "int", "liters": "float", "count": "int", "avg": "float",
        })
        self.daily_milk_vs_fullday_fmt = FormatForNeon(schema={
            "datex": "timestamp", "milkings": "int", "wy": "float",
            "heldback": "float", "wy_heldback": "float", "cp_adj": "float",
            "cp_actual": "float", "wy_minus_cp": "float",
        })

    def load_and_process(self):
        if {"tenday", "halfday"} & self.targets:
            self.MA = get_dependency('milk_aggregates')
        if {"fullday", "fullday_stats"} & self.targets:
            self.MAB = get_dependency('milk_aggregates_basic')
        if "wb_groups" in self.targets:
            self.WG = get_dependency('whiteboard_groups')
        if "max_days_per_period" in self.targets:
            self.WD = get_dependency('wet_dry')
        if "lactation_totals_live" in self.targets:
            self.L = get_dependency('lactations')
        if "daily_milk_vs_fullday" in self.targets:
            self.DMVF = get_dependency('daily_milk_vs_fullday')

        self.createDailyData()
        self.write_to_neon(get_engine(branch=self.branch))

    def createDailyData(self):
        """Pull raw dataframes only. Dtype coercion happens in FormatForNeon at write time."""
        if "tenday" in self.targets:
            self.tenday_formatted = self.MA.tenday.copy()
        if "halfday" in self.targets:
            self.halfday_formatted = self.MA.halfday.copy()
        if "fullday" in self.targets:
            self.fullday_formatted = self.MAB.fullday.copy()
        if "wb_groups" in self.targets:
            self.wb_groups_formatted = self.WG.whiteboard_groups_tenday.copy()
        if "max_days_per_period" in self.targets:
            self.max_days_per_period_formatted = self.WD.max_days_per_period.copy()
        if "lactation_totals_live" in self.targets:
            self.lactation_totals_live_formatted = self.L.lactation_totals_live.copy()
        if "fullday_stats" in self.targets:
            self.fullday_stats_formatted = self.MAB.fullday_stats.copy()
        if "daily_milk_vs_fullday" in self.targets:
            self.daily_milk_vs_fullday_formatted = self.DMVF.daily_milk_vs_fullday.copy()

    def write_to_neon(self, engine):
        with engine.begin() as conn:
            if "tenday" in self.targets:
                self.tenday_fmt.write_conn(self.tenday_formatted, 'tenday_formatted', conn, pk_col='wy_id')
            if "halfday" in self.targets:
                self.halfday_fmt.write_conn(self.halfday_formatted, 'halfday_formatted', conn)
            if "fullday" in self.targets:
                self.fullday_fmt.write_conn(self.fullday_formatted, 'fullday_formatted', conn, indexed_date=True)
            if "wb_groups" in self.targets:
                self.groups_fmt.write_conn(self.wb_groups_formatted, 'wb_groups_formatted', conn, pk_col='wy_id')
            if "max_days_per_period" in self.targets:
                self.max_days_per_period_fmt.write_conn(
                    self.max_days_per_period_formatted, 'max_days_per_period_formatted', conn, pk_col='wy_id')
            if "lactation_totals_live" in self.targets:
                self.lactation_totals_live_fmt.write_conn(
                    self.lactation_totals_live_formatted, 'lactation_totals_live_formatted', conn, pk_col='wy_id')
            if "fullday_stats" in self.targets:
                self.fullday_stats_fmt.write_conn(
                    self.fullday_stats_formatted, 'fullday_stats_formatted', conn, pk_col='wy_id')
            if "daily_milk_vs_fullday" in self.targets:
                self.daily_milk_vs_fullday_fmt.write_conn(
                    self.daily_milk_vs_fullday_formatted, 'daily_milk_vs_fullday_formatted', conn, pk_col='datex')


if __name__ == "__main__":
    print("Starting daily_modal.py")
    try:
        modal = DailyModal()
        modal.load_and_process()
        print("Completed load_and_process")
    except Exception as e:
        print(f"Error: {e}")