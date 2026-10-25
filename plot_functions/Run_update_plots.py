
'''plot_functions/Run_update_plots.py: Concierge runner for plot classes'''
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from container import get_dependency

def main():
    # Run lactation plot
    # run_lactation_plot = get_dependency('run_lactation_plot')
    # run_lactation_plot.load()
    # run_lactation_plot.process()

    # Run net revenue plot
    # plot_net_revenue_model = get_dependency('plot_net_revenue_model')
    # plot_net_revenue_model.load_and_process()

# Run plot_cum_net_revenue_periods
    plot_cum_net_revenue_periods = get_dependency('plot_cum_net_revenue_periods')
    plot_cum_net_revenue_periods.load()

if __name__ == "__main__":
    main()
