import yaml
import sys
try:
    from matplotlib import pyplot as plt
    from camilladsp_plot.plot_pipeline import plot_pipeline
    from camilladsp_plot.plot_filters import plot_filters, plot_all_filtersteps
except ImportError:
    plt = None

def prepare_config(conf):
    srate = conf['devices']['samplerate']
    channels = conf['devices']['capture']['channels']

    if 'filters' in conf:
        for _filt, fconf in conf['filters'].items():
            if fconf['type'] == 'Conv':
                if 'parameters' in fconf:
                    if "filename" in fconf['parameters']:
                        fconf['parameters']["filename"] = fconf['parameters']["filename"].replace("$samplerate$", str(srate))
                        fconf['parameters']["filename"] = fconf['parameters']["filename"].replace("$channels$", str(channels))

    if 'pipeline' in conf:
        for step in conf['pipeline']:
            if step['type'] == 'Mixer':
                step['name'] = step['name'].replace("$samplerate$", str(srate))
                step['name'] = step['name'].replace("$channels$", str(channels))
            elif step['type'] == 'Filter':
                for i, name in enumerate(step['names']):
                    name = name.replace("$samplerate$", str(srate))
                    name = name.replace("$channels$", str(channels))


def main():
    if plt is None:
        print("Matplotlib is not available! Can't display plots.")
        return
    fname = sys.argv[1]

    conffile = open(fname)

    conf = yaml.safe_load(conffile)
    prepare_config(conf)

    plot_pipeline(conf)
    plot_filters(conf)
    plot_all_filtersteps(conf)

    plt.show()

if __name__ == "__main__":
    main()