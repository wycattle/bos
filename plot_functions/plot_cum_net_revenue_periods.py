'''plot_cum_net_revenue_periods.py'''
import io
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from pipeline.aws.s3_loader import s3_upload_png

PERIOD_CSV = "/home/alanw/Documents/vsCode_output/wet_dry/wet_period_weekly.csv"
CUM_CSV = "/home/alanw/Documents/vsCode_output/finance/cumulative_avg_net_revenue_by_cow_weekly.csv"
HEIF_PRICE_CSV = "/home/alanw/Documents/vsCode_output/finance/heifer_price.csv"

# same destination as plot_net_revenue_model
S3_NET_REVENUE_PREFIX = "plots/Net_Revenue"

FEED_CHANGE_DATE1 = pd.Timestamp('2025-09-24')

BG = {
    'H': "#314d70",   # heifer
    'W': "#70314d",   # wet
    'D': "#4d7031",   # dry
}


class PlotCumNetRevenuePeriods:
    def load(self):
        self.cum = pd.read_csv(CUM_CSV, index_col=0, parse_dates=True).sort_index()
        self.period = pd.read_csv(PERIOD_CSV, index_col=0, parse_dates=True).sort_index()
        self.cum.columns = self.cum.columns.astype(str)
        self.period.columns = self.period.columns.astype(str)

        # heifer prices: plain read, wy_id normalised to str ("237", not 237 / 237.0)
        hp = pd.read_csv(HEIF_PRICE_CSV)
        hp.columns = [str(c).strip() for c in hp.columns]
        print(f"heifer_price.csv columns: {list(hp.columns)}")
        if 'wy_id' not in hp.columns or 'price' not in hp.columns:
            print("WARNING: heifer_price.csv needs 'wy_id' and 'price' columns")
            self.heifer_prices = {}
        else:
            hp['wy_id'] = (pd.to_numeric(hp['wy_id'], errors='coerce')
                           .dropna().astype(int).astype(str))
            hp['price'] = pd.to_numeric(hp['price'], errors='coerce').fillna(0)
            hp = hp.dropna(subset=['wy_id'])
            self.heifer_prices = dict(zip(hp['wy_id'], hp['price']))
        print(f"{len(self.heifer_prices)} heifer prices loaded")

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

        fig, ax = plt.subplots(figsize=(14, 8))  # the ONLY figure

        # period background shading
        if key in self.period.columns:
            codes = self.period[key]
            codes = codes[(codes.index >= dates.min()) & (codes.index <= dates.max())]
            for start, end, code in self._runs(codes):
                colour = self._shade_for(code)
                if colour is None:
                    continue
                ax.axvspan(start, end, color=colour, alpha=0.7, zorder=0, lw=0)
                ax.text(start + (end - start) / 2, 0.95, code,
                        transform=ax.get_xaxis_transform(),
                        ha='center', va='center', fontsize=20)

        # cumulative bars
        colors = ["#192638" if v >= 0 else "#ED5E5E" for v in s.values]
        ax.bar(dates, s.values, color=colors, width=5, alpha=0.9, zorder=2)

        # y-limits: always leave room for the heifer line (max price 65,000)
        y_min = s.min()
        y_max = max(s.max(), 70000)
        ax.set_ylim(y_min, y_max)

        # zero line
        ax.axhline(0, color='black', lw=1.0, zorder=3)

        # feed change marker (only if it falls within this cow's plotted range)
        if dates.min() <= FEED_CHANGE_DATE1 <= dates.max() + pd.Timedelta(days=7):
            ax.axvline(FEED_CHANGE_DATE1, color="#ECF016", linestyle='-',
                       linewidth=3, alpha=0.9, zorder=5,
                       label=f'Feed change: {FEED_CHANGE_DATE1:%y/%m/%d}')

        # heifer price line (price is 0, 45000 or 65000; 0 = no line)
        heifer_price = float(self.heifer_prices.get(key, 0))
        if heifer_price > 0:
            ax.axhline(heifer_price, color="#F21325", linestyle='-', linewidth=4,
                       alpha=0.8, zorder=4,
                       label=f'Heifer Price: {heifer_price:,.0f} baht')
        elif key not in self.heifer_prices:
            print(f"WARNING: no heifer price row for wy_id {key}")

        # legend: shows whichever lines were drawn (heifer price and/or feed change)
        if ax.get_legend_handles_labels()[0]:
            ax.legend(fontsize=12, loc='lower left',
                      bbox_to_anchor=(0, 1.01), borderaxespad=0)

        # axes and grid
        ax.set_ylabel('baht')
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))
        ax.tick_params(axis='y', labelsize=14)
        ticks = pd.date_range(dates.min(), dates.max(), freq='28D')
        ax.set_xticks(ticks)
        ax.set_xticklabels([d.strftime('%y/%m/%d') for d in ticks], rotation=45, fontsize=14)
        ax.grid(axis='y', linestyle='--', alpha=0.6, zorder=1)
        ax.set_xlim(dates.min(), dates.max() + pd.Timedelta(days=7))

        ax.set_title(f'Cumulative Avg Net Revenue - WY {wy_id}', fontsize=20, pad=22)

        # backgrounds
        fig.patch.set_facecolor("#957979")
        fig.patch.set_alpha(0.5)
        ax.set_facecolor('#3a3a3a')

        for spine in ax.spines.values():
            spine.set_edgecolor("#16020B")
            spine.set_linewidth(2)

        plt.tight_layout()

        # upload to S3 (same key as plot_net_revenue_model => overwrites)
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        plt.close(fig)
        buf.seek(0)
        s3_upload_png(S3_NET_REVENUE_PREFIX, f"cow_{wy_id}_net_revenue.png", buf.read())


if __name__ == "__main__":
    PlotCumNetRevenuePeriods().load()