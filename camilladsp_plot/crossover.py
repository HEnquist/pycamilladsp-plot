"""
Linear-phase FIR crossover filters, mirroring src/filters/crossover.rs in CamillaDSP.

The lowpass magnitude is 1/(1+r(x)) and the highpass is r(x)/(1+r(x)), with x the
prewarped normalized frequency and r(x) ~ x^n, where n = slope/6.
The FIR length, and thereby the latency, is chosen so that the truncation error
stays below TRUNCATION_TOLERANCE. The latency must match CamillaDSP exactly.

NOTE: this is a copy of the algorithm in CamillaDSP, src/filters/crossover.rs.
The latency must match CamillaDSP exactly, so any change must be made in BOTH places,
and the expected latencies in the tests of both repos must be updated.
"""

import math
from functools import lru_cache

TRUNCATION_TOLERANCE = 1.0e-5
ODD_ORDER_SMOOTHING = 0.01
MIN_DESIGN_FFT = 1 << 15
MAX_DESIGN_FFT = 1 << 23


def _numpy():
    try:
        import numpy
    except ImportError as err:
        raise ImportError("Crossover filters require numpy") from err
    return numpy


def lowpass_magnitude(freqs, samplerate, freq, slope):
    """Target lowpass magnitude (linear) at the given frequencies."""
    np = _numpy()
    order = slope // 6
    freqs = np.asarray(freqs, dtype=float)
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        x = np.tan(np.pi * np.minimum(freqs, samplerate / 2.0) / samplerate) / math.tan(
            math.pi * freq / samplerate
        )
        x = np.abs(x)
        if order % 2:
            eps = ODD_ORDER_SMOOTHING
            r = (x * x + eps * eps) ** (order / 2.0) - eps**order
        else:
            r = x**order
        magn = 1.0 / (1.0 + r)
    return np.where(freqs >= samplerate / 2.0, 0.0, magn)


@lru_cache(maxsize=64)
def _prototype(samplerate, freq, slope):
    """One side of the zero-phase lowpass impulse response, element 0 is the center tap."""
    np = _numpy()
    nfft = MIN_DESIGN_FFT
    while True:
        bins = np.arange(nfft // 2 + 1) * samplerate / nfft
        magn = lowpass_magnitude(bins, samplerate, freq, slope)
        half = np.fft.irfft(magn, nfft)[: nfft // 2 + 1]
        tail = np.cumsum((2.0 * np.abs(half))[::-1])[::-1]
        above = np.nonzero(tail >= TRUNCATION_TOLERANCE)[0]
        latency = int(above[-1]) if len(above) else 0
        if latency < nfft // 4 or nfft >= MAX_DESIGN_FFT:
            return half[: latency + 1].copy()
        nfft *= 2


def latency(samplerate, parameters):
    """Latency in samples of a crossover filter."""
    return len(_prototype(samplerate, float(parameters["freq"]), parameters["slope"])) - 1


def coefficients(samplerate, parameters):
    """FIR coefficients of a crossover filter."""
    np = _numpy()
    half = _prototype(samplerate, float(parameters["freq"]), parameters["slope"])
    lowpass = np.concatenate((half[:0:-1], half))
    if parameters["type"] == "Highpass":
        highpass = -lowpass
        highpass[len(half) - 1] += 1.0
        return highpass
    return lowpass


def filter_latencies(config, samplerate=None):
    """Latency in samples for each crossover filter defined in the config."""
    if samplerate is None:
        samplerate = config["devices"]["samplerate"]
    filters = config.get("filters") or {}
    return {
        name: latency(samplerate, conf["parameters"])
        for name, conf in filters.items()
        if conf.get("type") == "Crossover"
    }


def pipeline_latency(config, samplerate=None):
    """
    Latency of the crossover filters through the pipeline, following the same
    rules as CamillaDSP: channels are aligned before each mixer and processor,
    and at the end of the pipeline.
    Returns a dict with the latency per filter, the unaligned latency per output
    channel and the total latency, all in samples.
    """
    if samplerate is None:
        samplerate = config["devices"]["samplerate"]
    per_filter = filter_latencies(config, samplerate)
    channels = config["devices"]["capture"].get("channels", 0)
    latencies = [0] * channels
    for step in config.get("pipeline") or []:
        if step.get("bypassed"):
            continue
        if step["type"] == "Mixer":
            mixer = config["mixers"][step["name"]]
            latencies = [max(latencies, default=0)] * mixer["channels"]["out"]
        elif step["type"] == "Processor":
            latencies = [max(latencies, default=0)] * len(latencies)
        elif step["type"] == "Filter":
            step_channels = step.get("channels")
            if step_channels is None:
                step_channels = range(len(latencies))
            added = sum(per_filter.get(name, 0) for name in step["names"])
            for channel in step_channels:
                if channel < len(latencies):
                    latencies[channel] += added
    return {
        "samplerate": samplerate,
        "filters": per_filter,
        "channels": latencies,
        "total": max(latencies, default=0),
    }
