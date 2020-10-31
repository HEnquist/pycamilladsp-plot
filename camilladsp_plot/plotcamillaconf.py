import yaml
import sys
try:
    from matplotlib import pyplot as plt
    from camilladsp_plot.plot_pipeline import plot_pipeline
    from camilladsp_plot.plot_filters import plot_filters, plot_all_filtersteps
except ImportError:
    plt = None

def main():
    if plt is None:
        print("Matplotlib is not available! Can't display plots.")
        return
    fname = sys.argv[1]

    conffile = open(fname)

    conf = yaml.safe_load(conffile)

    plot_pipeline(conf)
    plot_filters(conf)
    plot_all_filtersteps(conf)

    plt.show()

if __name__ == "__main__":
    main()