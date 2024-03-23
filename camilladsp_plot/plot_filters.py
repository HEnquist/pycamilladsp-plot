from camilladsp_plot.eval_filterconfig import eval_filter, eval_filterstep
import matplotlib
from matplotlib import pyplot as plt
import io


def plot_filter(filterconf, name=None, samplerate=44100, npoints=1000, toimage=False):
    if toimage:
        matplotlib.use('Agg')
    filterdata = eval_filter(filterconf, name, samplerate, npoints)
    if filterconf['type'] in ('Biquad', 'DiffEq', 'BiquadCombo', 'Delay', 'Gain'):
        plt.figure(num=name)
        fplot = filterdata["f"]
        magn = filterdata["magnitude"]
        phase = filterdata["phase"]
        f_grp = filterdata["f_groupdelay"]
        groupdelay = filterdata["groupdelay"]
        plt.subplot(3, 1, 1)
        plt.semilogx(fplot, magn)
        plt.title(f"{name}")
        plt.ylabel("Magnitude, dB")
        plt.subplot(3, 1, 2)
        plt.semilogx(fplot, phase)
        plt.ylabel("Phase, deg")
        plt.subplot(3, 1, 3)
        plt.semilogx(f_grp, groupdelay)
        plt.ylabel("Group delay, ms")

    elif filterconf['type'] == 'Conv':
        plt.figure(num=name)
        fplot = filterdata["f"]
        magn = filterdata["magnitude"]
        phase = filterdata["phase"]
        t = filterdata["time"]
        impulse = filterdata["impulse"]
        f_grp = filterdata["f_groupdelay"]
        groupdelay = filterdata["groupdelay"]
        plt.subplot(4, 1, 1)
        plt.semilogx(fplot, magn)
        plt.title("{}".format(name))
        plt.ylabel("Magnitude, dB")
        plt.gca().set(xlim=(10, samplerate/2.0))
        plt.subplot(4, 1, 2)
        plt.plot(t, impulse)
        plt.ylabel("Impulse response")
        plt.subplot(4, 1, 3)
        plt.semilogx(fplot, phase)
        plt.ylabel("Phase, deg")
        plt.gca().set(xlim=(10, samplerate/2.0))
        plt.subplot(4, 1, 4)
        plt.semilogx(f_grp, groupdelay)
        plt.ylabel("Group delay, ms")
        plt.gca().set(xlim=(10, samplerate/2.0))
    if toimage:
        buf = io.BytesIO()
        plt.savefig(buf, format='svg')
        buf.seek(0)
        plt.close()
        return buf


def plot_filters(conf, overrides=None):
    srate = conf['devices']['samplerate']
    if overrides is not None and overrides.get('samplerate') is not None and conf["devices"].get("resampler") is None:
        srate = overrides['samplerate']
    if 'filters' in conf and conf['filters'] is not None:
        for filter, fconf in conf['filters'].items():
            plot_filter(fconf, samplerate=srate, name=filter)


def plot_filterstep(conf, pipelineindex, name="filterstep", npoints=1000, toimage=False, overrides=None):
    if toimage:
        matplotlib.use('Agg')
    filterdata = eval_filterstep(conf, pipelineindex, name, npoints, overrides=overrides)
    fplot = filterdata["f"]
    magn = filterdata["magnitude"]
    phase = filterdata["phase"]
    plt.figure(num=name)
    plt.subplot(2, 1, 1)
    plt.semilogx(fplot, magn)
    plt.title(name)
    plt.ylabel("Magnitude")
    plt.subplot(2, 1, 2)
    plt.semilogx(fplot, phase)
    plt.ylabel("Phase")
    if toimage:
        buf = io.BytesIO()
        plt.savefig(buf, format='svg')
        buf.seek(0)
        plt.close()
        return buf


def plot_all_filtersteps(conf, npoints=1000, toimage=False, overrides=None):
    if 'pipeline' in conf and conf['pipeline'] is not None:
        for idx, step in enumerate(conf['pipeline']):
            if step["type"] == "Filter":
                plot_filterstep(conf, idx, name="Pipeline step {}".format(
                    idx), npoints=npoints, toimage=toimage, overrides=overrides)
