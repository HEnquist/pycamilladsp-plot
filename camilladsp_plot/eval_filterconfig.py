import math
import cmath
from .filters import (
    BaseFilter,
    Biquad,
    BiquadCombo,
    Conv,
    Delay,
    DiffEq,
    Gain,
    Loudness,
    calc_groupdelay,
)


def logspace(minval, maxval, npoints):
    logmin = math.log10(minval)
    logmax = math.log10(maxval)
    perstep = (logmax - logmin) / npoints
    values = [10.0 ** (logmin + n * perstep) for n in range(npoints)]
    return values


def eval_filter(filterconf, name=None, samplerate=44100, npoints=1000, volume=0.0):
    fvect = logspace(1.0, samplerate * 0.95 / 2.0, npoints)
    if name is None:
        name = "unnamed {}".format(filterconf["type"])
    result = {"name": name, "samplerate": samplerate, "f": fvect}
    if filterconf["type"] in ("Biquad", "DiffEq", "BiquadCombo"):
        if filterconf["type"] == "DiffEq":
            currfilt = DiffEq(filterconf["parameters"], samplerate)
        elif filterconf["type"] == "BiquadCombo":
            currfilt = BiquadCombo(filterconf["parameters"], samplerate)
        else:
            currfilt = Biquad(filterconf["parameters"], samplerate)

        _fplot, magn, phase = currfilt.gain_and_phase(fvect)
        result["magnitude"] = magn
        result["phase"] = phase

    elif filterconf["type"] == "Conv":
        if "parameters" in filterconf:
            currfilt = Conv(filterconf["parameters"], samplerate)
        else:
            currfilt = Conv(None, samplerate)
        _ftemp, magn, phase = currfilt.gain_and_phase(fvect, remove_delay=True)
        t, impulse = currfilt.get_impulse()
        result["magnitude"] = magn
        result["phase"] = phase
        result["time"] = t
        result["impulse"] = impulse

    elif filterconf["type"] == "Delay":
        currfilt = Delay(filterconf["parameters"], samplerate)
        _fplot, magn, phase = currfilt.gain_and_phase(fvect)
        result["magnitude"] = magn
        result["phase"] = phase

    elif filterconf["type"] == "Gain":
        currfilt = Gain(filterconf["parameters"])
        _fplot, magn, phase = currfilt.gain_and_phase(fvect)
        result["magnitude"] = magn
        result["phase"] = phase

    elif filterconf["type"] == "Loudness":
        currfilt = Loudness(filterconf["parameters"], samplerate, volume)
        _fplot, magn, phase = currfilt.gain_and_phase(fvect)
        result["magnitude"] = magn
        result["phase"] = phase

    elif filterconf["type"] in ("Volume", "Dither"):
        currfilt = BaseFilter()
        _fplot, magn, phase = currfilt.gain_and_phase(fvect)
        result["magnitude"] = magn
        result["phase"] = phase

    else:
        raise ValueError(f"Unknown filter type {filterconf['type']}")

    f_grp, groupdelay = calc_groupdelay(result["f"], result["phase"])
    result["f_groupdelay"] = f_grp
    result["groupdelay"] = groupdelay
    # result["phase"] = unwrap_phase(result["phase"])
    return result


def eval_filterstep(
    conf, pipelineindex, name="filterstep", npoints=1000, overrides=None
):
    samplerate = conf["devices"]["samplerate"]
    if (
        overrides is not None
        and overrides.get("samplerate") is not None
        and conf["devices"].get("resampler") is None
    ):
        samplerate = overrides["samplerate"]
    fvect = logspace(10.0, samplerate * 0.95 / 2.0, npoints)
    pipelinestep = conf["pipeline"][pipelineindex]
    totcgain = [1.0 for n in range(npoints)]
    for filt in pipelinestep["names"]:
        filterconf = conf["filters"][filt]
        if filterconf["type"] == "DiffEq":
            currfilt = DiffEq(filterconf["parameters"], samplerate)
        elif filterconf["type"] == "BiquadCombo":
            currfilt = BiquadCombo(filterconf["parameters"], samplerate)
        elif filterconf["type"] == "Biquad":
            currfilt = Biquad(filterconf["parameters"], samplerate)
        elif filterconf["type"] == "Conv":
            currfilt = Conv(filterconf["parameters"], samplerate)
        elif filterconf["type"] == "Gain":
            currfilt = Gain(filterconf["parameters"])
        elif filterconf["type"] == "Delay":
            currfilt = Delay(filterconf["parameters"], samplerate)
        else:
            continue
        _, cgainstep = currfilt.complex_gain(fvect)
        totcgain = [cg * cgstep for (cg, cgstep) in zip(totcgain, cgainstep)]
    gain = [20.0 * math.log10(abs(cg) + 1.0e-15) for cg in totcgain]
    phase = [180 / math.pi * cmath.phase(cg) for cg in totcgain]
    f_grp, groupdelay = calc_groupdelay(fvect, phase)
    result = {
        "name": name,
        "samplerate": samplerate,
        "f": fvect,
        "magnitude": gain,
        "phase": phase,
        "f_groupdelay": f_grp,
        "groupdelay": groupdelay,
    }
    return result
