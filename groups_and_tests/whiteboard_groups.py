'''groups_and_tests/whiteboard_groups.py'''

import inspect
import pandas as pd

from container import get_dependency
from pipeline.neon.neon_connect import get_engine, read_sql_table_traced


class WhiteboardGroups:

    GROUP_ORDER = ["fresh", "group_A", "group_B", "group_C", "sick"]

    def __init__(self):
        print(f"WhiteboardGroups instantiated by: {inspect.stack()[1].filename}")
        self.engine = get_engine()

        # inputs
        self.start      = pd.to_datetime("2026-09-10")
        self.am_wy      = None
        self.counts     = None
        self.tenday_avg = None
        self.allx       = pd.DataFrame()

        # outputs
        self.group_data               = {}   # {group: {date: [wy_id, ...]}, ...}
        self.whiteboard_groups_tenday = pd.DataFrame()

    def load(self):
        self.IUD = get_dependency('insem_ultra_data')
        self.MA  = get_dependency('milk_aggregates')
        self.process()

    def process(self):
        # ---------- query ----------
        with self.engine.connect() as conn:
            am_wy        = read_sql_table_traced('AM_wy', conn)
            group_counts = read_sql_table_traced('group_counts', conn)

        # ---------- normalize dates ----------
        am_wy["date"]         = pd.to_datetime(am_wy["date"]).dt.normalize()
        group_counts["datex"] = pd.to_datetime(group_counts["datex"]).dt.normalize()

        # ---------- last day (group_counts drives the date) ----------
        am_wy        = am_wy[am_wy["date"] >= self.start]
        last_day     = am_wy["date"].max()
        group_counts = group_counts[group_counts["datex"] == last_day]

        # ---------- keep only that day's rows ----------
        self.am_wy  = am_wy[am_wy["date"] == last_day].set_index("date").sort_index()
        self.counts = group_counts.set_index(["datex", "group_name"]).sort_index()

        # ---------- schema: {group: count} in GROUP_ORDER, from group_counts ----------
        self.schema = (
            self.counts.xs(last_day, level="datex")["count"]
            .reindex(self.GROUP_ORDER)
            .fillna(0)
            .astype(int)
        )

        # ---------- slice the ordered c1..cN series by the schema ----------
        c_cols = sorted(
            [c for c in self.am_wy.columns if c.lower().startswith("c") and c[1:].isdigit()],
            key=lambda c: int(c[1:])
        )
        row    = self.am_wy.iloc[0]
        values = [row[c] for c in c_cols if pd.notna(row[c])]

        assert sum(self.schema) == len(values), (last_day, sum(self.schema), len(values))  # schema must consume the whole series

        self.group_data = {g: {} for g in self.GROUP_ORDER}
        pos = 0
        for g, n in self.schema.items():
            self.group_data[g][last_day] = values[pos:pos + n]
            pos += n

        # ---------- cow attributes + tenday average ----------
        self.allx       = self.IUD.allx
        self.tenday_avg = self.MA.tenday.loc[:, ['wy_id', 'avg']].set_index('wy_id')

        # ---------- flatten + enrich ----------
        self.whiteboard_groups_tenday = self.build_whiteboard_groups()

    def build_whiteboard_groups(self) -> pd.DataFrame:
        rows = [
            {'wy_id': wy_id, 'group_name': group, 'snapshot_date': date}
            for group, date_map in self.group_data.items()
            for date, wy_ids in date_map.items()
            for wy_id in wy_ids
        ]
        if not rows:
            return pd.DataFrame()

        wbg = pd.DataFrame(rows)

        # keep each wy_id's most recent assignment
        wbg = wbg.sort_values('snapshot_date').drop_duplicates('wy_id', keep='last')

        # merge tenday average
        wbg = wbg.merge(self.tenday_avg, how='left', left_on='wy_id', right_index=True)

        # merge cow attributes
        days = self.allx.loc[:, ['wy_id', 'days_milking', 'u_read', 'expected_bdate']]
        wbg  = wbg.merge(days, how='left', on='wy_id')

        wbg = wbg.sort_values('avg', ascending=False).reset_index(drop=True)

        self.whiteboard_groups_tenday = wbg
        return self.whiteboard_groups_tenday

if __name__ == "__main__":
    obj = WhiteboardGroups()
    obj.load()
    print(obj.whiteboard_groups_tenday)