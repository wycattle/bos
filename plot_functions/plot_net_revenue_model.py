'''plot_functions/plot_net_revenue_model.py'''
import io
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from container import get_dependency
from pipeline.aws.s3_loader import s3_upload_png 
S3_NET_REVENUE_PREFIX = "plots/Net_Revenue"

class PlotNetRevenueModel:
    def __init__(self):
        pass
    def load(self):
        self.NR = get_dependency('net_revenue')
        self.SD = get_dependency('status_data')
        self.DOC= get_dependency('date_of_change')  
        self.process()

    def process(self):
        self.total_income_weekly      = self.NR.total_income_weekly
        self.feedcost_weekly    = self.NR.feedcost_weekly
        self.net_revenue_weekly = self.NR.net_revenue_weekly
        self.alive_ids_today    = self.SD.alive_ids_today
        self.date_of_change1    = self.DOC.date_of_change1
        self.date_of_change2    = self.DOC.date_of_change2
        self.plot_all_live_cows()

    def plot_all_live_cows(self):
        for wy_id in self.alive_ids_today:
            self.plot_one_cow(wy_id)

    def plot_one_cow(self, wy_id):
        cols = {}
        for name, wide_df in (
            ('revenue', self.total_income_weekly),
            ('feedcost', self.feedcost_weekly),
            ('net_revenue', self.net_revenue_weekly),
        ):
            cols[name] = wide_df[wy_id] if wy_id in wide_df.columns else pd.Series(index=wide_df.index, dtype=float)

        cow_df = pd.DataFrame(cols).sort_index()
        if cow_df.isnull().all().all():
            return  # nothing to plot for this cow

        dates = cow_df.index

        fig, ax1 = plt.subplots(figsize=(14, 8))
        ax1.fill_between(dates, 0, cow_df['feedcost'], color="#C18DA7", alpha=0.5, label='Feedcost')
        ax1.bar(dates, cow_df['revenue'], color="#265755", label='Revenue', width=4, alpha=0.5)
        ax1.set_ylabel('Weekly Revenue / Feedcost', color='black')
        ax1.tick_params(axis='y', labelcolor='black')

        ax2 = ax1.twinx()
        ax2.plot(dates, cow_df['net_revenue'], 'o-', color='purple', label='Net Revenue')
        ax2.set_ylabel('Weekly Net Revenue', color='purple')
        ax2.tick_params(axis='y', labelcolor='purple')

        week_ticks = pd.date_range(dates.min(), dates.max(), freq='14D')
        ax1.set_xticks(week_ticks)
        ax1.set_xticklabels([dt.strftime('%m/%d') for dt in week_ticks], rotation=90)
        for tick in week_ticks:
            ax1.axvline(tick, color='gray', linestyle=':', alpha=0.3, zorder=0)

        if pd.notna(self.date_of_change1):
            ax1.axvline(self.date_of_change1, color='green', linestyle='--', linewidth=2, label='Day of Change 1')
        if pd.notna(self.date_of_change2):
            ax1.axvline(self.date_of_change2, color='red', linestyle='--', linewidth=2, label='Day of Change 2')

        ax1.grid(axis='y', linestyle='--', alpha=0.7)
        ax1.set_xlim(dates.min(), dates.max())

        handles1, labels1 = ax1.get_legend_handles_labels()
        handles2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(handles1 + handles2, labels1 + labels2, loc='upper center', facecolor='lightgreen', framealpha=0.25)

        plt.title(f'Net Revenue - WY {wy_id}', fontsize=20)
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        plt.close(fig)  # explicit fig, not bare plt.close() — see note below
        buf.seek(0)
        s3_upload_png(S3_NET_REVENUE_PREFIX, f"cow_{wy_id}_net_revenue.png", buf.read())


if __name__ == "__main__":
    obj = PlotNetRevenueModel()
    obj.load()