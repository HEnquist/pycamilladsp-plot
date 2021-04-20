import yaml
import sys
from camilladsp_plot.validate_config import CamillaValidator
try:
    from matplotlib import pyplot as plt
    from camilladsp_plot.plot_pipeline import plot_pipeline
    from camilladsp_plot.plot_filters import plot_filters, plot_all_filtersteps
except ImportError:
    plt = None


def main():

    fname = sys.argv[1]

    #conffile = open(fname)

    #conf = yaml.safe_load(conffile)
    #prepare_config(conf)
    validator = CamillaValidator()
    validator.validate_file(fname)
    errors = validator.get_errors()
    if len(errors) == 0:
        if plt is None:
            print("Matplotlib is not available! Can't display plots.")
            return
        conf = validator.get_config()
        plot_pipeline(conf)
        plot_filters(conf)
        plot_all_filtersteps(conf)
        plt.show()
    else: 
        print("Unable to plot, config has errors:")
        for err in errors:
            print("/".join([str(p) for p in err[0]]), " : ",  err[1])

if __name__ == "__main__":
    main()