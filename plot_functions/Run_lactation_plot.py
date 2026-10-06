'''plot_functions.run_lactation_plot'''
import os
import matplotlib
from pathlib import Path
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from container import get_dependency
import pandas as pd
import numpy as np

class RunLactationPlot:
    def __init__(self):
        self.output_folder = str(Path.home() / "gdrive_mount" / "COWS" / "plots" / "Lactation_plots")
        os.makedirs(self.output_folder, exist_ok=True)
        self.TL = None
        self.LLS = None
        self.doc = None
        self.df_weekly = None
        self.df_daily = None
        self.df_id_list = None
        self.weekly_avg_all = None
        self.daily_avg_all = None

    def load(self):
        self.TL = get_dependency('this_lactation')
        self.LLS = get_dependency('lactations_log_standard')
        self.doc = self.LLS.days_on_date_of_change1
        # Example/test access (can be removed or kept for debug)
        cow_idx = 94
        _ = self.doc.iloc[self.doc.index.get_loc(cow_idx), 0]

        self.df_weekly = self.TL.milking_wkly.iloc[:53, :].copy().dropna(axis=1, how='all')
        self.df_daily  = self.TL.milking_daily.iloc[:364, :].copy().dropna(axis=1, how='all')
        self.df_id_list = self.df_weekly.columns.to_frame(index=False, name="wy_id")
        self.df_id_list.to_csv(os.path.join(self.output_folder, "cow_id_list.csv"), index=False)

        self.weekly_avg_all = self.df_weekly.mean(axis=1)
        self.daily_avg_all  = self.df_daily.mean(axis=1)

    def process(self):
        for cow_id in self.df_weekly.columns:
            days_on_date_of_change1 = None
            if self.doc is not None:
                try:
                    cow_id_int = int(cow_id)
                    value = self.doc.iloc[self.doc.index.get_loc(cow_id_int), 0]
                    if not pd.isna(value) and value > 0:
                        days_on_date_of_change1 = value
                except Exception as e:
                    print(f"Error for cow_id {cow_id}: {e}")

            fig, ax1 = plt.subplots(figsize=(14, 8))
            # Plot the average weekly line (blue)
            ax1.plot(self.df_weekly.index, self.weekly_avg_all.values, '-', color='blue', label='weekly avg_liters/day - all cows', alpha=.8)
            # Plot the individual cow weekly (red)
            ax1.plot(self.df_weekly.index, self.df_weekly[cow_id].values, 'o-', color='red', label=f'weekly avg_liters/day - WY#{cow_id}')
            ax1.set_xlabel('Weeks Milking')
            ax1.set_ylabel('Liters', color='blue')
            ax1.tick_params(axis='y', labelcolor='blue')
            ax1.grid(axis='y', linestyle='--', alpha=0.7)
            ax1.grid(axis='x', linestyle=':', alpha=0.7)
            ax1.set_xlim(self.df_weekly.index.min(), self.df_weekly.index.max())

            # Plot daily data for this cow if available
            if cow_id in self.df_daily.columns:
                ax2 = ax1.twiny()
                ax2.plot(self.df_daily.index, self.df_daily[cow_id].values, 
                         linestyle='-', 
                         linewidth=1, 
                         marker='o',
                         markersize=1,
                         color='orange', 
                         label=f'Cow wy_id {cow_id} (daily avg_liters)', 
                         alpha=0.7)
                ax2.set_xlabel('Days Milking')
                ax2.set_xlim(self.df_daily.index.min(), self.df_daily.index.max())
                day_ticks = np.arange(self.df_daily.index.min(), self.df_daily.index.max() + 1, 7)
                ax2.set_xticks(day_ticks)
                ax2.set_xticklabels(day_ticks, rotation=90)
                ax2.grid(axis='x', linestyle=':', alpha=0.3)

                # Draw vertical gridline if days_on_date_of_change1 is valid
                if days_on_date_of_change1 is not None:
                    ax2.axvline(days_on_date_of_change1, color='green', linestyle='--', linewidth=3, label='Date of Change')

                # Combine legends
                lines1, labels1 = ax1.get_legend_handles_labels()
                lines2, labels2 = ax2.get_legend_handles_labels()
                ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
            else:
                ax1.legend(loc='upper right')

            plt.title(f'WY {cow_id}', fontsize=20)
            plt.tight_layout()
            output_path = os.path.join(self.output_folder, f"cow_{cow_id}_weekly_daily.png")
            plt.savefig(output_path)
            plt.close()

if __name__ == "__main__":
    plotter = RunLactationPlot()
    plotter.load()
    plotter.process()
