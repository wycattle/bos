'''milk_functions/daily_milk_vs_fullday.py

Compares what the farm measured (wy, from the whiteboard) with what the
buyer paid for (cp, from the receipts), one row per calendar day.

Background
----------
The buyer collects milk every other day. A pickup contains several milkings,
not one day. In the normal case the truck comes after the morning milking:

    pickup on day D (4 milkings):
        AM of D, PM of D-1, AM of D-1, PM of D-2

So one receipt covers parts of three days. To compare it with the farm
numbers, each receipt is divided equally over the milkings it contains, and
those shares are added up per calendar day (AM share + PM share = that day's
cp_adj). The receipt as recorded is kept separately as cp_actual.

Terminology
-----------
milking slot   One milking: the AM or PM milking of one date.
slot index     Integer id of a slot. AM of a date = 2 * date_ordinal,
               PM of the same date = 2 * date_ordinal + 1. Consecutive
               milkings have consecutive slot indexes.
pickup         A row of daily_milk that has a sale_total (buyer receipt).
window         The consecutive slots one pickup contains. Windows are CHAINED:
               each starts right after the previous one ended, so together
               they tile the timeline with no gaps and no overlaps.
cp_adj         A day's share of the buyer receipts (receipts spread over the
               milkings they contain, then added up per day).
cp_actual      The receipt exactly as recorded, shown only on its pickup date.
'''

import inspect
import pandas as pd
from pathlib import Path
from pipeline.neon.neon_connect import get_engine, read_sql_table_traced


class DailyMilkVsFullday:
    '''Farm milk vs buyer receipts, per day, with receipts spread over the
    milkings they actually contain.

    Inputs (read from Neon):
        daily_milk     One row per date, filled from the Google Sheet:
                       sale_total      buyer receipt, only on pickup days
                       milkings        number of milkings in that pickup
                                       (normally 4; type 5 or 3 for an
                                       irregular pickup)
                       sick_am, sick_pm, heifers_am, heifers_pm
                                       liters held back from the tank
        milkings_long  View: one row per milking (date, type, liters) from
                       milk_transpose. type is 'AM_liters' or 'PM_liters'.

    Output (self.daily_milk_vs_fullday), one row per complete day:
        datex          the day
        milkings       window size of the pickup that happened on this day
                       (4 normally; 5 or 3 flags an irregular pickup);
                       0 on days without a pickup, as in the Sheet
        wy             farm liters, AM + PM of that day
        heldback       liters held back, AM + PM of that day
        wy_heldback    wy - heldback (what should have gone into the tank)
        cp_adj         that day's share of the buyer receipts
        cp_actual      the receipt as recorded, on pickup dates only
                       (0 on other days)
        wy_minus_cp    wy_heldback - cp_adj (positive = farm measured more
                       than the buyer paid for)
    '''

    OUTPUT_COLUMNS = [
        'datex', 'milkings', 'wy', 'heldback', 'wy_heldback',
        'cp_adj', 'cp_actual', 'wy_minus_cp',
    ]
    HELDBACK_SOURCE_COLUMNS = ['sick_am', 'sick_pm', 'heifers_am', 'heifers_pm']
    DAILY_MILK_REQUIRED_COLUMNS = ['datex', 'sale_total'] + HELDBACK_SOURCE_COLUMNS
    MILKING_LITERS_REQUIRED_COLUMNS = ['date', 'type', 'liters']
    ROWS_TO_KEEP = 10
    OUTPUT_DIR = Path("/home/alanw/Documents/vsCode_output/milk")

    def __init__(self):
        '''Create an empty instance. Nothing is read until load() is called.'''
        print(f"DailyMilkVsFullday instantiated by: {inspect.stack()[1].filename}")
        self.engine = None
        self.daily_milk = pd.DataFrame()              # buyer / held-back / milkings rows from Neon
        self.milking_liters = pd.DataFrame()          # one row per milking: date, type, liters
        self.daily_milk_vs_fullday = pd.DataFrame()   # final result

    # ------------------------------------------------------------ entry points
    def load(self):
        '''Open the Neon connection and run the whole pipeline.'''
        self.engine = get_engine()
        self.process()

    def process(self):
        '''Read inputs, build the per-day comparison, and write the CSV.'''
        self.daily_milk, self.milking_liters = self._read_neon_query()
        self.daily_milk_vs_fullday = self.compare_wy_cp()
        self.write_to_csv()

    # -------------------------------------------------------------------- read
    def _read_neon_query(self):
        '''Read both Neon inputs and normalise their types.

        Returns:
            (daily_milk, milking_liters) as DataFrames.
            daily_milk is sorted by date; datex is a datetime64 column.
            milking_liters has a datetime64 'date' column and float 'liters'
            (Neon NUMERIC arrives as Decimal, which pandas cannot sum).
        '''
        with self.engine.connect() as conn:
            daily_milk = read_sql_table_traced('daily_milk', conn)
            milking_liters = read_sql_table_traced('milkings_long', conn)

        self._require_columns(daily_milk, self.DAILY_MILK_REQUIRED_COLUMNS, 'daily_milk')
        self._require_columns(milking_liters, self.MILKING_LITERS_REQUIRED_COLUMNS, 'milkings_long')

        daily_milk['datex'] = pd.to_datetime(daily_milk['datex'])
        daily_milk = daily_milk.sort_values('datex').reset_index(drop=True)

        milking_liters['date'] = pd.to_datetime(milking_liters['date'])
        milking_liters['liters'] = milking_liters['liters'].astype(float)
        return daily_milk, milking_liters

    @staticmethod
    def _require_columns(frame, required_columns, table_name):
        '''Raise a clear error if a Neon table is missing columns we rely on.

        Args:
            frame: DataFrame that was read from Neon.
            required_columns: column names that must be present.
            table_name: name used in the error message.
        '''
        missing = [c for c in required_columns if c not in frame.columns]
        if missing:
            raise KeyError(f"{table_name} is missing columns: {missing}")

    # ----------------------------------------------------------- slot helpers
    @staticmethod
    def _to_slot_index(dates):
        '''Convert dates to the slot index of that date's AM milking.

        AM slot = 2 * date_ordinal; the PM slot of the same date is that
        value + 1.

        Args:
            dates: Series of dates (any datetime-like dtype).
        Returns:
            Series of integers, same index as `dates`.
        '''
        return 2 * pd.to_datetime(dates).dt.normalize().map(pd.Timestamp.toordinal)

    @staticmethod
    def _slot_index_to_date(slot_indexes):
        '''Convert slot indexes back to the calendar date they belong to.

        Args:
            slot_indexes: integer slot indexes (an Index or numpy array).
        Returns:
            DatetimeIndex of the corresponding dates (the AM and PM slots of
            one day map to the same date).
        '''
        return pd.to_datetime(
            [pd.Timestamp.fromordinal(int(i)) for i in (slot_indexes // 2)]
        )

    # ------------------------------------------------------------ per-slot series
    def _farm_liters_by_slot(self):
        '''Farm liters for every milking slot.

        Returns:
            Series named 'wy', indexed by slot index.
        '''
        milkings = self.milking_liters.copy()
        is_pm = (milkings['type'] == 'PM_liters').astype(int)
        milkings['slot_index'] = self._to_slot_index(milkings['date']) + is_pm
        return milkings.groupby('slot_index')['liters'].sum().rename('wy')

    def _heldback_liters_by_slot(self, daily):
        '''Held-back liters for every milking slot.

        The Sheet records held-back milk per day as an AM part
        (sick_am + heifers_am) and a PM part (sick_pm + heifers_pm). These
        are placed on that date's AM slot and PM slot respectively.

        Args:
            daily: copy of daily_milk with a 'slot_index' column (AM slot of
                   each date) and the held-back columns already numeric.
        Returns:
            Series named 'heldback', indexed by slot index.
        '''
        am_heldback = pd.Series(
            (daily['sick_am'] + daily['heifers_am']).values,
            index=daily['slot_index'].values,
        )
        pm_heldback = pd.Series(
            (daily['sick_pm'] + daily['heifers_pm']).values,
            index=daily['slot_index'].values + 1,
        )
        return (
            pd.concat([am_heldback, pm_heldback])
            .groupby(level=0).sum()
            .rename('heldback')
        )

    # ----------------------------------------------------------- pickup windows
    def _pickups_with_windows(self, daily):
        '''Select pickup rows and give each one a window of milking slots.

        Windows are chained so they tile with no gaps or overlaps: a pickup's
        window starts right after the previous pickup's window ended and
        contains `milkings` slots. The window's last slot must be the AM or PM
        milking of the pickup's own date:
            AM = truck came after the morning milking (the normal case)
            PM = truck came after the evening milking (this is how an
                 irregular 5-then-3 sequence fits together)

        Rules:
            * The first pickup in the data only anchors the chain (assumed to
              end at AM). It produces a window only if it has a milkings value.
            * If the Sheet's milkings is blank or 0, the gap from the previous
              window's end to this date's AM is used instead.
            * If the chained end does not land on this pickup's date, a note is
              printed and the chain is reset to this date's AM slot. One typo
              therefore cannot corrupt every later row.
            * Pickups with no usable window size are skipped.

        Args:
            daily: copy of daily_milk with 'slot_index' (AM slot of each date).
        Returns:
            DataFrame with columns: datex, end_slot_index, milkings_in_window
            (int), sale_total. One row per pickup that has a usable window.
        '''
        pickups = daily.dropna(subset=['sale_total']).sort_values('slot_index')
        sheet_window_sizes = pd.to_numeric(pickups['milkings'], errors='coerce')
        sheet_window_sizes = sheet_window_sizes.where(sheet_window_sizes > 0)

        window_rows = []
        previous_end_slot = None
        for pickup_date, am_slot, receipt_total, sheet_window_size in zip(
            pickups['datex'],
            pickups['slot_index'],
            pickups['sale_total'].astype(float),
            sheet_window_sizes,
        ):
            pm_slot = am_slot + 1

            if previous_end_slot is None:
                end_slot = int(am_slot)
                window_size = sheet_window_size
            else:
                if pd.notna(sheet_window_size):
                    window_size = int(sheet_window_size)
                else:
                    window_size = int(am_slot - previous_end_slot)

                chained_end_slot = int(previous_end_slot + window_size)
                if window_size > 0 and chained_end_slot in (am_slot, pm_slot):
                    end_slot = chained_end_slot
                    if end_slot == pm_slot:
                        print(f"  note {pickup_date:%Y-%m-%d}: window ends at PM milking "
                              f"(pickup after evening milking)")
                else:
                    print(f"  note {pickup_date:%Y-%m-%d}: milkings={window_size} does not "
                          f"chain from the previous pickup; reset to AM milking")
                    end_slot = int(am_slot)

            if pd.notna(window_size) and window_size > 0:
                window_rows.append(
                    (pickup_date, end_slot, int(window_size), receipt_total)
                )
            previous_end_slot = end_slot

        return pd.DataFrame(
            window_rows,
            columns=['datex', 'end_slot_index', 'milkings_in_window', 'sale_total'],
        )

    def _cp_adj_by_slot(self, pickups):
        '''Spread each receipt equally over the milking slots of its window.

        For a pickup whose window ends at slot E and has W milkings, slots
        E-W+1 ... E each get sale_total / W. If windows overlap on a slot the
        shares add up (a note is printed, because that double-counts).

        Args:
            pickups: output of _pickups_with_windows().
        Returns:
            Series named 'cp_adj' (this slot's share of the receipts),
            indexed by slot index.
        '''
        share_rows = []
        for end_slot, window_size, receipt_total in zip(
            pickups['end_slot_index'],
            pickups['milkings_in_window'],
            pickups['sale_total'],
        ):
            for slot_index in range(end_slot - window_size + 1, end_slot + 1):
                share_rows.append((slot_index, receipt_total / window_size))

        shares = pd.DataFrame(share_rows, columns=['slot_index', 'cp_adj'])

        overlapping = shares['slot_index'].duplicated(keep=False)
        if overlapping.any():
            overlap_dates = sorted(set(
                self._slot_index_to_date(shares.loc[overlapping, 'slot_index'].unique())
                .strftime('%Y-%m-%d')
            ))
            print("  note: pickup windows overlap on these dates (cp_adj is double-counted):",
                  overlap_dates)

        return shares.groupby('slot_index')['cp_adj'].sum()

    # ------------------------------------------------------------------ compare
    def compare_wy_cp(self):
        '''Build the per-day farm-vs-buyer comparison.

        Steps:
            1. Farm liters and held-back liters per milking slot.
            2. Chained pickup windows; each receipt divided over its slots
               (cp_adj).
            3. Keep slots that have all three pieces of data.
            4. Add slots up per date; keep only dates with both AM and PM.
            5. Compute wy_heldback and wy_minus_cp (using cp_adj).
            6. Label pickup dates with their window size (milkings) and the
               receipt as recorded (cp_actual); 0 on other days.

        Returns:
            DataFrame with OUTPUT_COLUMNS, the most recent ROWS_TO_KEEP days.
            Also stored in self.daily_milk_vs_fullday. After a normal
            AM-ending pickup, that day's PM milking belongs to the next
            pickup, so the newest day appears only once the next pickup
            has been entered.
        '''
        daily = self.daily_milk.copy()
        if 'milkings' not in daily.columns:
            daily['milkings'] = float('nan')
        daily['slot_index'] = self._to_slot_index(daily['datex'])
        for column in self.HELDBACK_SOURCE_COLUMNS:
            daily[column] = daily[column].fillna(0).astype(float)

        farm_liters_by_slot = self._farm_liters_by_slot()
        heldback_by_slot = self._heldback_liters_by_slot(daily)

        pickups = self._pickups_with_windows(daily)
        if pickups.empty:
            print("  note: no usable pickups found")
            return self._empty_result()
        cp_adj_by_slot = self._cp_adj_by_slot(pickups)

        # keep only slots where farm, held-back and buyer data all exist
        slot_table = (
            farm_liters_by_slot.to_frame()
            .join(heldback_by_slot)
            .join(cp_adj_by_slot)
            .dropna()
        )
        if slot_table.empty:
            print("  note: no slots have farm, held-back and buyer data together")
            return self._empty_result()
        slot_table['datex'] = self._slot_index_to_date(slot_table.index)

        by_day = slot_table.groupby('datex').agg(
            wy=('wy', 'sum'),
            heldback=('heldback', 'sum'),
            cp_adj=('cp_adj', 'sum'),
            slots_present=('wy', 'size'),
        )
        by_day = by_day[by_day['slots_present'] == 2].drop(columns='slots_present').reset_index()

        by_day['wy_heldback'] = by_day['wy'] - by_day['heldback']
        by_day['wy_minus_cp'] = by_day['wy_heldback'] - by_day['cp_adj']

        # milkings and cp_actual are shown only on the date of the pickup (0 elsewhere)
        window_size_by_pickup_date = pickups.set_index('datex')['milkings_in_window']
        by_day['milkings'] = (
            by_day['datex'].map(window_size_by_pickup_date).fillna(0).astype(int)
        )
        receipt_by_pickup_date = (
            daily.dropna(subset=['sale_total'])
            .set_index('datex')['sale_total']
            .astype(float)
        )
        by_day['cp_actual'] = by_day['datex'].map(receipt_by_pickup_date).fillna(0.0)

        result = by_day[self.OUTPUT_COLUMNS].tail(self.ROWS_TO_KEEP).reset_index(drop=True)
        self.daily_milk_vs_fullday = result
        return result

    def _empty_result(self):
        '''Return an empty result with the right columns (used when there is
        not enough data), and store it on the instance.'''
        self.daily_milk_vs_fullday = pd.DataFrame(columns=self.OUTPUT_COLUMNS)
        return self.daily_milk_vs_fullday

    # -------------------------------------------------------------------- write
    def write_to_csv(self):
        '''Write the result to daily_milk_vs_fullday.csv in OUTPUT_DIR
        (created if needed), without the pandas index column.'''
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.daily_milk_vs_fullday.to_csv(
            self.OUTPUT_DIR / "daily_milk_vs_fullday.csv", index=False
        )


if __name__ == '__main__':
    obj = DailyMilkVsFullday()
    obj.load()