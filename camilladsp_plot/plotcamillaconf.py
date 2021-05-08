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
    if len(sys.argv) < 2:
        print("Please give a config filename!")
        return
    fname = sys.argv[1]
    validator = CamillaValidator()
    validator.validate_file(fname)
    errors = validator.get_errors()
    warnings = validator.get_warnings()
    if len(errors) == 0:
        if len(warnings) > 0:
            print("Warnings:")
            for w in warnings:
                print("/".join([str(p) for p in w[0]]), " : ",  w[1])
        if plt is None:
            print("Matplotlib is not available! Can't display plots.")
            return
        #conf = validator.get_config()
        conf = validator.get_processed_config()
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