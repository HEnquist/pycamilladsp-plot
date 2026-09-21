import math

import pytest

np = pytest.importorskip("numpy")

from camilladsp_plot import crossover
from camilladsp_plot.eval_filterconfig import eval_filter
from camilladsp_plot.validate_config import CamillaValidator


def _params(ftype, freq, slope):
    return {"type": ftype, "freq": freq, "slope": slope}


# Keep in sync with CamillaDSP, src/filters/crossover.rs, test known_latencies
@pytest.mark.parametrize(
    "samplerate, freq, slope, expected",
    [
        (44100, 80.0, 24, 1375),
        (48000, 80.0, 24, 1496),
        (48000, 40.0, 12, 2199),
        (48000, 80.0, 48, 2795),
        (48000, 80.0, 96, 5566),
        (48000, 2500.0, 96, 180),
        (48000, 1000.0, 18, 369),
        (48000, 10000.0, 30, 18),
    ],
)
def test_latency_matches_camilladsp(samplerate, freq, slope, expected):
    assert crossover.latency(samplerate, _params("Lowpass", freq, slope)) == expected
    assert crossover.latency(samplerate, _params("Highpass", freq, slope)) == expected


@pytest.mark.parametrize("slope", [12, 18, 24, 48, 96])
def test_lowpass_plus_highpass_is_pure_delay(slope):
    lp = crossover.coefficients(48000, _params("Lowpass", 1000.0, slope))
    hp = crossover.coefficients(48000, _params("Highpass", 1000.0, slope))
    expected = np.zeros(len(lp))
    expected[len(lp) // 2] = 1.0
    assert np.max(np.abs(lp + hp - expected)) < 1e-12


@pytest.mark.parametrize("ftype", ["Lowpass", "Highpass"])
def test_eval_crossover_minus_6_db_at_crossover(ftype):
    conf = {"type": "Crossover", "parameters": _params(ftype, 2000.0, 48)}
    result = eval_filter(conf, samplerate=48000, npoints=500)
    idx = min(range(500), key=lambda n: abs(result["f"][n] - 2000.0))
    # Frequency grid does not hit 2000 Hz exactly, the slope is steep
    assert abs(result["magnitude"][idx] + 6.02) < 1.0
    assert result["latency"] > 0
    assert len(result["impulse"]) == 2 * result["latency"] + 1


def test_pipeline_latency_aligns_channels():
    config = {
        "devices": {"samplerate": 48000, "capture": {"channels": 1}},
        "mixers": {"split": {"channels": {"in": 1, "out": 4}}},
        "filters": {
            "lp80": {"type": "Crossover", "parameters": _params("Lowpass", 80.0, 48)},
            "hp80": {"type": "Crossover", "parameters": _params("Highpass", 80.0, 48)},
            "lp2500": {"type": "Crossover", "parameters": _params("Lowpass", 2500.0, 96)},
            "hp2500": {"type": "Crossover", "parameters": _params("Highpass", 2500.0, 96)},
        },
        "pipeline": [
            {"type": "Mixer", "name": "split"},
            {"type": "Filter", "channels": [0], "names": ["lp80"]},
            {"type": "Filter", "channels": [1], "names": ["hp80", "lp2500"]},
            {"type": "Filter", "channels": [2], "names": ["hp2500"]},
        ],
    }
    result = crossover.pipeline_latency(config)
    assert result["channels"] == [2795, 2975, 180, 0]
    assert result["total"] == 2975


def _validate(parameters):
    config = {
        "devices": {
            "samplerate": 48000,
            "chunksize": 1024,
            "capture": {"type": "Stdin", "channels": 2, "format": "S16_LE"},
            "playback": {"type": "Stdout", "channels": 2, "format": "S16_LE"},
        },
        "filters": {"xo": {"type": "Crossover", "parameters": parameters}},
        "pipeline": [{"type": "Filter", "names": ["xo"]}],
    }
    validator = CamillaValidator()
    validator.validate_config(config)
    return validator.get_errors()


def test_validation_accepts_valid_crossover():
    assert _validate(_params("Lowpass", 1000.0, 24)) == []


@pytest.mark.parametrize(
    "parameters",
    [
        _params("Lowpass", 1000.0, 6),
        _params("Lowpass", 1000.0, 25),
        _params("Lowpass", 1000.0, 102),
        _params("Highpass", 30000.0, 24),
        _params("Bandpass", 1000.0, 24),
        {"type": "Lowpass", "freq": 1000.0},
    ],
)
def test_validation_rejects_invalid_crossover(parameters):
    assert _validate(parameters) != []
