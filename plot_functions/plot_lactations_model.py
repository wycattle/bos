'''plot_functions/lactation_plots.py'''
import io
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from container import get_dependency
from pipeline.aws.s3_loader import s3_upload_png

S3_LACTATION_PREFIX = "plots/lactations"  # changed from "plots/Lactation_Curves"


class LactationPlots:
    def __init__(self):
        self.L = None
        self.LB = None
        self.SD = None
        self.alive_ids = None
        self.weekly_lactations = None

    def load(self):
        self.L = get_dependency('lactations')
        self.LB = get_dependency('lactation_basics')
        self.SD = get_dependency('StatusData')
        self.process()

    def process(self):
        self.alive_ids = self.SD.alive_ids_today
        self.weekly_lactations = [
            (1, self.L.live_L1_weekly_avg),
            (2, self.L.live_L2_weekly_avg),
            (3, self.L.live_L3_weekly_avg),
            (4, self.L.live_L4_weekly_avg),
            (5, self.L.live_L5_weekly_avg),
            (6, self.L.live_L6_weekly_avg),
        ]

    def plot_all_live_cows(self):
        for wy_id in self.alive_ids:
            self.plot_one_cow(wy_id)

    def plot_one_cow(self, wy_id):
        wy_str = str(wy_id)
        wy_int = int(wy_id) if pd.notna(wy_id) else None

        # Determine ongoing lactation number for this cow
        ongoing_lact = None
        if self.LB.ongoing_lactations is not None and wy_int is not None:
            ongoing_lact = self.LB.ongoing_lactations.get(wy_int)

        colors = ['C0', 'C1', 'C2', 'C3', 'C4', 'C5']

        fig, ax = plt.subplots(figsize=(12, 6))

        plotted_any = False
        for lact_num, weekly_df in self.weekly_lactations:
            if wy_str not in weekly_df.columns:
                continue

            cow_series = weekly_df[wy_str]
            cow_series = cow_series.where(cow_series > 0)  # hide zero-padding
            if cow_series.dropna().empty:
                continue

            weeks = cow_series.index + 1
            is_ongoing = (ongoing_lact is not None and lact_num == ongoing_lact)
            label = f'Lactation {lact_num}'
            if is_ongoing:
                label += ' (ongoing)'

            ax.plot(
                weeks,
                cow_series,
                marker='o',
                markersize=3,
                linewidth=2,
                color=colors[lact_num - 1],
                label=label,
                linestyle='--' if is_ongoing else '-',
                alpha=0.9
            )
            plotted_any = True

        if not plotted_any:
            plt.close(fig)
            return

        ax.set_xlabel('Week of Lactation')
        ax.set_ylabel('Average Daily Milk Yield (kg)')
        ax.set_title(f'Lactation Curves - WY {wy_str}')
        ax.grid(True, linestyle='--', alpha=0.7)
        ax.legend()

        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        plt.close(fig)
        buf.seek(0)
        s3_upload_png(S3_LACTATION_PREFIX, f"cow_{wy_str}_lactation_curves.png", buf.read())


if __name__ == "__main__":
    obj = LactationPlots()
    obj.load()
    obj.plot_all_live_cows()