'''plot_cum_net_revenue_periods.py'''
import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

PERIOD_CSV = "/home/alanw/Documents/vsCode_output/wet_dry/wet_period_weekly.csv"
CUM_CSV = "/home/alanw/Documents/vsCode_output/finance/cumulative_avg_net_revenue_by_cow_weekly.csv"
OUT_DIR = "/home/alanw/Documents/vsCode_output/finance/plots/Cum_Net_Revenue_Periods"

# letter -> (odd-number shade, even-number shade)
BG = {
    'H': ("#314d70"),   # heifer
    'W': ("#70314d"),   # wet
    'D': ("#4d7031"),   # dry
}


class PlotCumNetRevenuePeriods:
    def load(self):
        self.cum = pd.read_csv(CUM_CSV, index_col=0, parse_dates=True).sort_index()
        self.period = pd.read_csv(PERIOD_CSV, index_col=0, parse_dates=True).sort_index()
        self.cum.columns = self.cum.columns.astype(str)
        self.period.columns = self.period.columns.astype(str)
        os.makedirs(OUT_DIR, exist_ok=True)
        self.alive_ids_today = self._live_ids()
        print(f"{len(self.alive_ids_today)} live cows")
        for wy_id in self.alive_ids_today:
            self.plot_one_cow(wy_id)

    def _live_ids(self):
        last = self.period.iloc[-1]
        return [c for c, v in last.items()
                if isinstance(v, str) and v[:1] in BG and c in self.cum.columns]

    @staticmethod
    def _shade_for(code):
        if not isinstance(code, str) or code[:1] not in BG:
            return None
        return BG[code[0]]

    @staticmethod
    def _runs(codes):
        """Collapse weekly codes into (start, end, code) runs."""
        runs, start, prev = [], None, None
        for dt, c in codes.items():
            if c != prev:
                if prev is not None:
                    runs.append((start, dt, prev))
                start, prev = dt, c
        if prev is not None:
            runs.append((start, codes.index[-1] + pd.Timedelta(days=7), prev))
        return runs

    def plot_one_cow(self, wy_id):
        key = str(wy_id)
        s = self.cum[key].dropna()
        if s.empty:
            return
        dates = s.index

        fig, ax = plt.subplots(figsize=(14, 8))

        handles = []
        if key in self.period.columns:
            codes = self.period[key]
            codes = codes[(codes.index >= dates.min()) & (codes.index <= dates.max())]
            seen = {}
            for start, end, code in self._runs(codes):
                colour = self._shade_for(code)
                if colour is None:
                    continue
                ax.axvspan(start, end, color=colour, alpha=0.7, zorder=0, lw=0)
                ax.text(start + (end - start) / 2, 0.95, code,
                        transform=ax.get_xaxis_transform(),
                        ha='center', va='center', fontsize=20)
                seen[code] = colour


        colors = ["#192638" if v >= 0 else "#ED5E5E" for v in s.values]
        #creates a bar plot
        ax.bar(dates, s.values,  color=colors, width = 5, alpha=0.9, zorder=2)


        # Calculate automatic y-limits based on data
        y_min = s.min()  # Lowest data value
        y_max = s.max()  # Highest data value

        # Adjust to ensure zero line is at least at y=1000
        if y_max < 65000:
            y_max = 65000  # Force zero line to be visible at y=1000
        elif y_max < 1000: # Only needed if you still want the 1000 minimum
            y_max = 1000

        ax.set_ylim(y_min, y_max)  # Set dynamic limits

        # Always show zero line
        ax.axhline(0, color='black', lw=1.0, zorder=3)

        # Configure axes and grid

        ax.set_ylabel('baht')
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))
        ax.tick_params(axis='y', labelsize=14)
        ticks = pd.date_range(dates.min(), dates.max(), freq='28D')
        ax.set_xticks(ticks)
        ax.set_xticklabels([d.strftime('%y/%m/%d') for d in ticks], rotation=45, fontsize=14)
        ax.grid(axis='y', linestyle='--', alpha=0.6, zorder=1)
        ax.set_xlim(dates.min(), dates.max() + pd.Timedelta(days=7))


        ax.set_title(f'Cumulative Avg Net Revenue - WY {wy_id}', fontsize=20, pad=22)

        # Set dark background for the entire figure
        fig.patch.set_facecolor("#957979")  # Dark gray background
        fig.patch.set_alpha(0.5)  # Opaque

        # Set slightly lighter background for just the plot area
        ax.set_facecolor('#3a3a3a')  # Medium gray plot background



        for spine in ax.spines.values():
            spine.set_edgecolor("#16020B") # Or choose any color you prefer
            spine.set_linewidth(2) # Thicker border


        plt.tight_layout()
        fig.savefig(os.path.join(OUT_DIR, f"cow_{wy_id}_cum_net_revenue_periods.png"))
        plt.close(fig)


if __name__ == "__main__":
    PlotCumNetRevenuePeriods().load()