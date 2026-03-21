import pytest

from camilladsp_plot.eval_filterconfig import eval_filter


def _assert_eval_result_shape(result, npoints):
    assert "f" in result
    assert "magnitude" in result
    assert "phase" in result
    assert "f_groupdelay" in result
    assert "groupdelay" in result
    assert len(result["f"]) == npoints
    assert len(result["magnitude"]) == npoints
    assert len(result["phase"]) == npoints
    assert len(result["f_groupdelay"]) == npoints - 1
    assert len(result["groupdelay"]) == npoints - 1


# === Shelf Filters (value checks) ===

def test_eval_biquad_lowshelf_has_expected_low_and_high_frequency_gain():
    npoints = 300
    filterconf = {
        "type": "Biquad",
        "parameters": {
            "type": "Lowshelf",
            "freq": 1000.0,
            "q": 0.707,
            "gain": 6.0,
        },
    }

    result = eval_filter(filterconf, samplerate=48000, npoints=npoints)

    _assert_eval_result_shape(result, npoints)
    assert abs(result["magnitude"][0] - 6.0) < 0.4
    assert abs(result["magnitude"][-1] - 0.0) < 0.4


def test_eval_biquad_highshelf_has_expected_low_and_high_frequency_gain():
    npoints = 300
    filterconf = {
        "type": "Biquad",
        "parameters": {
            "type": "Highshelf",
            "freq": 1000.0,
            "q": 0.707,
            "gain": 6.0,
        },
    }

    result = eval_filter(filterconf, samplerate=48000, npoints=npoints)

    _assert_eval_result_shape(result, npoints)
    assert abs(result["magnitude"][0] - 0.0) < 0.4
    assert abs(result["magnitude"][-1] - 6.0) < 0.4


# === Other Biquad Types (smoke checks) ===

@pytest.mark.parametrize(
    "biquad_params",
    [
        {"type": "Lowpass", "freq": 1000.0, "q": 0.707},
        {"type": "Highpass", "freq": 1000.0, "q": 0.707},
        {"type": "Peaking", "freq": 1000.0, "q": 1.0, "gain": 3.0},
        {"type": "Notch", "freq": 1000.0, "q": 5.0},
        {
            "type": "GeneralNotch",
            "freq_pole": 1200.0,
            "q_pole": 2.0,
            "freq_zero": 1000.0,
            "normalize_at_dc": False,
        },
        {"type": "Bandpass", "freq": 1000.0, "q": 2.0},
        {"type": "Allpass", "freq": 1000.0, "q": 0.9},
        {"type": "AllpassFO", "freq": 1000.0},
        {"type": "LowpassFO", "freq": 1000.0},
        {"type": "HighpassFO", "freq": 1000.0},
        {"type": "LowshelfFO", "freq": 1000.0, "gain": 3.0},
        {"type": "HighshelfFO", "freq": 1000.0, "gain": 3.0},
        {
            "type": "LinkwitzTransform",
            "freq_act": 60.0,
            "q_act": 0.7,
            "freq_target": 30.0,
            "q_target": 0.8,
        },
        {
            "type": "Free",
            "a1": -0.5,
            "a2": 0.2,
            "b0": 1.0,
            "b1": 0.0,
            "b2": 0.0,
        },
    ],
)
def test_eval_biquad_other_types_return_result_without_exceptions(biquad_params):
    npoints = 128
    result = eval_filter(
        {"type": "Biquad", "parameters": biquad_params},
        samplerate=48000,
        npoints=npoints,
    )
    _assert_eval_result_shape(result, npoints)


# === BiquadCombo Filters ===

def test_eval_biquadcombo_graphic_equalizer_with_zero_gains_is_flat():
    npoints = 200
    filterconf = {
        "type": "BiquadCombo",
        "parameters": {
            "type": "GraphicEqualizer",
            "freq_min": 20.0,
            "freq_max": 20000.0,
            "gains": [0.0, 0.0, 0.0, 0.0, 0.0],
        },
    }

    result = eval_filter(filterconf, samplerate=48000, npoints=npoints)

    _assert_eval_result_shape(result, npoints)
    assert max(abs(value) for value in result["magnitude"]) < 1e-6


def test_eval_biquadcombo_tilt_positive_gain_tilts_up_towards_high_frequencies():
    npoints = 300
    filterconf = {
        "type": "BiquadCombo",
        "parameters": {
            "type": "Tilt",
            "gain": 10.0,
        },
    }

    result = eval_filter(filterconf, samplerate=48000, npoints=npoints)

    _assert_eval_result_shape(result, npoints)
    assert result["magnitude"][0] < -1.0
    assert result["magnitude"][-1] > 1.0


@pytest.mark.parametrize(
    "combo_params",
    [
        {"type": "ButterworthHighpass", "freq": 1000.0, "order": 4},
        {"type": "ButterworthLowpass", "freq": 1000.0, "order": 4},
        {"type": "LinkwitzRileyHighpass", "freq": 1000.0, "order": 4},
        {"type": "LinkwitzRileyLowpass", "freq": 1000.0, "order": 4},
        {
            "type": "FivePointPeq",
            "fls": 80.0,
            "fp1": 200.0,
            "fp2": 800.0,
            "fp3": 2400.0,
            "fhs": 6000.0,
            "qls": 0.7,
            "qp1": 1.0,
            "qp2": 1.0,
            "qp3": 1.0,
            "qhs": 0.7,
            "gls": 1.0,
            "gp1": -1.0,
            "gp2": 0.5,
            "gp3": -0.5,
            "ghs": 1.0,
        },
    ],
)
def test_eval_biquadcombo_other_types_return_result_without_exceptions(combo_params):
    npoints = 128
    result = eval_filter(
        {"type": "BiquadCombo", "parameters": combo_params},
        samplerate=48000,
        npoints=npoints,
    )
    _assert_eval_result_shape(result, npoints)


# === Conv Filters ===

def test_eval_conv_identity_values_is_flat_and_returns_impulse_data():
    npoints = 128
    filterconf = {
        "type": "Conv",
        "parameters": {
            "type": "Values",
            "values": [1.0],
        },
    }

    result = eval_filter(filterconf, samplerate=48000, npoints=npoints)

    _assert_eval_result_shape(result, npoints)
    assert "time" in result
    assert "impulse" in result
    assert result["impulse"] == [1.0]
    assert len(result["time"]) == 1
    assert max(abs(value) for value in result["magnitude"]) < 1e-6


def test_eval_conv_two_tap_values_returns_result_without_exceptions():
    npoints = 128
    filterconf = {
        "type": "Conv",
        "parameters": {
            "type": "Values",
            "values": [0.5, 0.5],
        },
    }

    result = eval_filter(filterconf, samplerate=48000, npoints=npoints)

    _assert_eval_result_shape(result, npoints)
    assert "time" in result
    assert "impulse" in result
    assert result["impulse"] == [0.5, 0.5]
    assert len(result["time"]) == 2