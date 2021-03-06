import cmath
import math
import csv
import yaml
import sys
import math
import itertools
import struct
from .cooley_tukey import fft


class Conv(object):

    TYPES_DIRECT = {
        "FLOAT64LE": "<d",
        "FLOAT32LE": "<f",
        "S16LE": "<h",
        "S32LE": "<i",
    }

    TYPES_INDIRECT = {
        "S24LE": {
            "pattern": "sssx",
            "endian": "little"
        },
        "S24LE3": {
            "pattern": "sss",
            "endian": "little"
        },
    }

    SCALEFACTOR = {
        "FLOAT64LE": 1.0,
        "FLOAT32LE": 1.0,
        "S16LE": (2 ** 15),
        "S24LE": (2 ** 23),
        "S24LE3": (2 ** 23),
        "S32LE": (2 ** 31),
    }

    BYTESPERSAMPLE = {
        "FLOAT64LE": 8,
        "FLOAT32LE": 4,
        "S16LE": 2,
        "S24LE": 4,
        "S24LE3": 3,
        "S32LE": 4,
    }

    def __init__(self, conf, fs):
        if not conf:
            conf = {"values": [1.0]}
        if "filename" in conf:
            values = self._read_coeffs(conf)
        else:
            values = conf["values"]
        self.impulse = values
        self.fs = fs

    def _read_coeffs(self, conf):
        fname = conf["filename"]
        if "format" not in conf:
            conf["format"] = "TEXT"
        if "read_bytes_lines" not in conf or conf["read_bytes_lines"] == 0:
            read_nbr = None
        else:
            read_nbr = conf["read_bytes_lines"]
        if "skip_bytes_lines" not in conf:
            skip_nbr = 0
        else:
            skip_nbr = conf["skip_bytes_lines"]
        if conf["format"] == "TEXT":
            values = self._read_text_coeffs(fname, skip_nbr, read_nbr)
        else:
            if conf["format"] in self.TYPES_DIRECT:
                values = self._read_binary_direct_coeffs(fname, conf["format"], skip_nbr, read_nbr)
            elif conf["format"] in self.TYPES_INDIRECT:
                values = self._read_binary_indirect_coeffs(fname, conf["format"], skip_nbr, read_nbr)
            else:
                raise ValueError(f"Unsupported format {conf['format']}")
        return values

    def _read_text_coeffs(self, fname, skip_lines, read_lines):
        with open(fname) as f:
            rawvalues = itertools.islice(csv.reader(f), skip_lines, read_lines)
            values = [float(row[0]) for row in rawvalues]
        return values

    def _read_binary_direct_coeffs(self, fname, sampleformat, skip_bytes, read_bytes):

        if read_bytes is None:
            count = -1
        else:
            count = read_bytes

        datatype = self.TYPES_DIRECT[sampleformat]
        factor = self.SCALEFACTOR[sampleformat]
        with open(fname, 'rb') as f:
            f.seek(skip_bytes)
            data = f.read(count)
        values = [float(val[0])/factor for val in struct.iter_unpack(datatype, data)]
        return values

    def _read_binary_indirect_coeffs(self, fname, sampleformat, skip_bytes, read_bytes):

        if read_bytes is None:
            count = -1
        else:
            count = read_bytes

        pattern = self.TYPES_INDIRECT[sampleformat]["pattern"]
        factor = self.SCALEFACTOR[sampleformat]
        endian = self.TYPES_INDIRECT[sampleformat]["endian"]
        with open(fname, 'rb') as f:
            f.seek(skip_bytes)
            data = f.read(count)
        values = [int.from_bytes(b"".join(val), endian, signed=True)/factor for val in struct.iter_unpack(pattern, data)]
        return values

    def complex_gain(self, f):
        impulselen = len(self.impulse)
        npoints = impulselen
        if npoints < 1024:
            npoints = 1024
        impulse = list(self.impulse)
        while len(impulse) < 2*npoints:
            impulse.append(0.0)
        impfft = fft(impulse)
        f_fft = [self.fs*n/(2.0*npoints) for n in range(npoints)]
        cut = impfft[0:npoints]
        if f is not None:
            interpolated = self.interpolate_polar(cut, f_fft, f)
            return f, interpolated
        return f_fft, cut

    def interpolate(self, y, xold, xnew):
        idx = 0
        ynew = []
        
        for x in xnew:
            idx = len(y)*x/xold[-1]
            i1 = int(math.floor(idx))
            i2 = i1+1
            if i1>=(len(y)):
                i1 = len(y)-1
            if i2>=(len(y)):
                i2 = i1
            fract = idx - i1
            newval = (1-fract)*y[i1] + fract*y[i2]
            ynew.append(newval)
        return ynew

    def interpolate_polar(self, y, xold, xnew):
        y_magn = [abs(yval) for yval in y]
        y_ang = [cmath.phase(yval) for yval in y]
        y_magn_interp = self.interpolate(y_magn, xold, xnew)
        y_ang_interp = self.interpolate(y_ang, xold, xnew)
        return [cmath.rect(r, phi) for (r, phi) in zip(y_magn_interp, y_ang_interp)]

    def gain_and_phase(self, f):
        f_fft, Avec = self.complex_gain(None)
        gain = [20 * math.log10(abs(A)) for A in Avec]
        gain = self.interpolate(gain, f_fft, f)
        phase = [180 / math.pi * cmath.phase(A) for A in Avec]
        phase = self.interpolate(phase, f_fft, f)
        return f, gain, phase

    def get_impulse(self):
        t = [n/self.fs for n in range(len(self.impulse))]
        return t, self.impulse


class DiffEq(object):
    def __init__(self, conf, fs):
        self.fs = fs
        self.a = conf["a"]
        self.b = conf["b"]
        if len(self.a) == 0:
            self.a = [1.0]
        if len(self.b) == 0:
            self.b = [1.0]

    def complex_gain(self, freq):
        zvec = [cmath.exp(1j * 2 * math.pi * f / self.fs) for f in freq]
        A1 = [0.0 for n in range(len(freq))]  
        for n, bn in enumerate(self.b):
            A1 = [a1 + bn * z ** (-n) for a1, z in zip(A1, zvec)]
        A2 = [0.0 for n in range(len(freq))]  
        for n, an in enumerate(self.a):
            A2 = [a2 + an * z ** (-n) for a2, z in zip(A2, zvec)]
        A = [a1 / a2 for (a1, a2) in zip(A1, A2)]
        return freq, A

    def gain_and_phase(self, f):
        _f, Avec = self.complex_gain(f)
        gain = [20 * math.log10(abs(A)) for A in Avec]
        phase = [180 / math.pi * cmath.phase(A) for A in Avec]
        return f, gain, phase

    def is_stable(self):
        # TODO
        return None


class Gain(object):
    def __init__(self, conf):
        self.gain = conf["gain"]
        self.inverted = conf["inverted"]

    def complex_gain(self, f):
        sign = -1.0 if self.inverted else 1.0
        gain = 10.0**(self.gain/20.0) * sign
        A = [gain for n in range(len(f))] 
        return f, A

    def gain_and_phase(self, f):
        Aval = 10.0**(self.gain/20.0)
        gain = [Aval for n in range(len(f))]       
        phaseval = 180 / math.pi if self.inverted else 0
        phase = [phaseval for n in range(len(f))]  
        return f, gain, phase

    def is_stable(self):
        return True


class BiquadCombo(object):
    def Butterw_q(self, order):
        odd = order % 2 > 0
        n_so = math.floor(order / 2.0)
        qvalues = []
        for n in range(0, n_so):
            q = 1 / (2.0 * math.sin((math.pi / order) * (n + 1 / 2)))
            qvalues.append(q)
        if odd:
            qvalues.append(-1.0)
        return qvalues

    def __init__(self, conf, fs):
        self.ftype = conf["type"]
        self.order = conf["order"]
        self.freq = conf["freq"]
        self.fs = fs
        if self.ftype == "LinkwitzRileyHighpass":
            # qvalues = self.LRtable[self.order]
            q_temp = self.Butterw_q(self.order / 2)
            if (self.order / 2) % 2 > 0:
                q_temp = q_temp[0:-1]
                qvalues = q_temp + q_temp + [0.5]
            else:
                qvalues = q_temp + q_temp
            type_so = "Highpass"
            type_fo = "HighpassFO"

        elif self.ftype == "LinkwitzRileyLowpass":
            q_temp = self.Butterw_q(self.order / 2)
            if (self.order / 2) % 2 > 0:
                q_temp = q_temp[0:-1]
                qvalues = q_temp + q_temp + [0.5]
            else:
                qvalues = q_temp + q_temp
            type_so = "Lowpass"
            type_fo = "LowpassFO"
        elif self.ftype == "ButterworthHighpass":
            qvalues = self.Butterw_q(self.order)
            type_so = "Highpass"
            type_fo = "HighpassFO"
        elif self.ftype == "ButterworthLowpass":
            qvalues = self.Butterw_q(self.order)
            type_so = "Lowpass"
            type_fo = "LowpassFO"
        self.biquads = []
        print(qvalues)
        for q in qvalues:
            if q >= 0:
                bqconf = {"freq": self.freq, "q": q, "type": type_so}
            else:
                bqconf = {"freq": self.freq, "type": type_fo}
            self.biquads.append(Biquad(bqconf, self.fs))

    def is_stable(self):
        # TODO
        return None

    def complex_gain(self, freq):
        A = [1.0 for n in range(len(freq))]
        for bq in self.biquads:
            _f, Atemp = bq.complex_gain(freq)
            A = [a*atemp for (a, atemp) in zip(A, Atemp)]
        return freq, A

    def gain_and_phase(self, f):
        _f, Avec = self.complex_gain(f)
        gain = [20 * math.log10(abs(A)) for A in Avec]
        phase = [180 / math.pi * cmath.phase(A) for A in Avec]
        return f, gain, phase


class Biquad(object):
    def __init__(self, conf, fs):
        ftype = conf["type"]
        if ftype == "Free":
            a0 = 1.0
            a1 = conf["a1"]
            a2 = conf["a1"]
            b0 = conf["b0"]
            b1 = conf["b1"]
            b2 = conf["b2"]
        if ftype == "Highpass":
            freq = conf["freq"]
            q = conf["q"]
            omega = 2.0 * math.pi * freq / fs
            sn = math.sin(omega)
            cs = math.cos(omega)
            alpha = sn / (2.0 * q)
            b0 = (1.0 + cs) / 2.0
            b1 = -(1.0 + cs)
            b2 = (1.0 + cs) / 2.0
            a0 = 1.0 + alpha
            a1 = -2.0 * cs
            a2 = 1.0 - alpha
        elif ftype == "Lowpass":
            freq = conf["freq"]
            q = conf["q"]
            omega = 2.0 * math.pi * freq / fs
            sn = math.sin(omega)
            cs = math.cos(omega)
            alpha = sn / (2.0 * q)
            b0 = (1.0 - cs) / 2.0
            b1 = 1.0 - cs
            b2 = (1.0 - cs) / 2.0
            a0 = 1.0 + alpha
            a1 = -2.0 * cs
            a2 = 1.0 - alpha
        elif ftype == "Peaking":
            freq = conf["freq"]
            q = conf["q"]
            gain = conf["gain"]
            omega = 2.0 * math.pi * freq / fs
            sn = math.sin(omega)
            cs = math.cos(omega)
            ampl = 10.0 ** (gain / 40.0)
            alpha = sn / (2.0 * q)
            b0 = 1.0 + (alpha * ampl)
            b1 = -2.0 * cs
            b2 = 1.0 - (alpha * ampl)
            a0 = 1.0 + (alpha / ampl)
            a1 = -2.0 * cs
            a2 = 1.0 - (alpha / ampl)
        elif ftype == "HighshelfFO":
            freq = conf["freq"]
            gain = conf["gain"]
            omega = 2.0 * math.pi * freq / fs
            ampl = 10.0 ** (gain / 40.0)
            tn = math.tan(omega / 2)
            b0 = ampl * tn + ampl ** 2
            b1 = ampl * tn - ampl ** 2
            b2 = 0.0
            a0 = ampl * tn + 1
            a1 = ampl * tn - 1
            a2 = 0.0
        elif ftype == "Highshelf":
            freq = conf["freq"]
            slope = conf["slope"]
            gain = conf["gain"]
            omega = 2.0 * math.pi * freq / fs
            ampl = 10.0 ** (gain / 40.0)
            sn = math.sin(omega)
            cs = math.cos(omega)
            alpha = (
                sn
                / 2.0
                * math.sqrt((ampl + 1.0 / ampl) * (1.0 / (slope / 12.0) - 1.0) + 2.0)
            )
            beta = 2.0 * math.sqrt(ampl) * alpha
            b0 = ampl * ((ampl + 1.0) + (ampl - 1.0) * cs + beta)
            b1 = -2.0 * ampl * ((ampl - 1.0) + (ampl + 1.0) * cs)
            b2 = ampl * ((ampl + 1.0) + (ampl - 1.0) * cs - beta)
            a0 = (ampl + 1.0) - (ampl - 1.0) * cs + beta
            a1 = 2.0 * ((ampl - 1.0) - (ampl + 1.0) * cs)
            a2 = (ampl + 1.0) - (ampl - 1.0) * cs - beta
        elif ftype == "LowshelfFO":
            freq = conf["freq"]
            gain = conf["gain"]
            omega = 2.0 * math.pi * freq / fs
            ampl = 10.0 ** (gain / 40.0)
            tn = math.tan(omega / 2)
            b0 = ampl ** 2 * tn + ampl
            b1 = ampl ** 2 * tn - ampl
            b2 = 0.0
            a0 = tn + ampl
            a1 = tn - ampl
            a2 = 0.0
        elif ftype == "Lowshelf":
            freq = conf["freq"]
            slope = conf["slope"]
            gain = conf["gain"]
            omega = 2.0 * math.pi * freq / fs
            ampl = 10.0 ** (gain / 40.0)
            sn = math.sin(omega)
            cs = math.cos(omega)
            alpha = (
                sn
                / 2.0
                * math.sqrt((ampl + 1.0 / ampl) * (1.0 / (slope / 12.0) - 1.0) + 2.0)
            )
            beta = 2.0 * math.sqrt(ampl) * alpha
            b0 = ampl * ((ampl + 1.0) - (ampl - 1.0) * cs + beta)
            b1 = 2.0 * ampl * ((ampl - 1.0) - (ampl + 1.0) * cs)
            b2 = ampl * ((ampl + 1.0) - (ampl - 1.0) * cs - beta)
            a0 = (ampl + 1.0) + (ampl - 1.0) * cs + beta
            a1 = -2.0 * ((ampl - 1.0) + (ampl + 1.0) * cs)
            a2 = (ampl + 1.0) + (ampl - 1.0) * cs - beta
        elif ftype == "LowpassFO":
            freq = conf["freq"]
            omega = 2.0 * math.pi * freq / fs
            k = math.tan(omega / 2.0)
            alpha = 1 + k
            a0 = 1.0
            a1 = -((1 - k) / alpha)
            a2 = 0.0
            b0 = k / alpha
            b1 = k / alpha
            b2 = 0
        elif ftype == "HighpassFO":
            freq = conf["freq"]
            omega = 2.0 * math.pi * freq / fs
            k = math.tan(omega / 2.0)
            alpha = 1 + k
            a0 = 1.0
            a1 = -((1 - k) / alpha)
            a2 = 0.0
            b0 = 1.0 / alpha
            b1 = -1.0 / alpha
            b2 = 0
        elif ftype == "Notch":
            freq = conf["freq"]
            q = conf["q"]
            omega = 2.0 * math.pi * freq / fs
            sn = math.sin(omega)
            cs = math.cos(omega)
            alpha = sn / (2.0 * q)
            b0 = 1.0
            b1 = -2.0 * cs
            b2 = 1.0
            a0 = 1.0 + alpha
            a1 = -2.0 * cs
            a2 = 1.0 - alpha
        elif ftype == "Bandpass":
            freq = conf["freq"]
            q = conf["q"]
            omega = 2.0 * math.pi * freq / fs
            sn = math.sin(omega)
            cs = math.cos(omega)
            alpha = sn / (2.0 * q)
            b0 = alpha
            b1 = 0.0
            b2 = -alpha
            a0 = 1.0 + alpha
            a1 = -2.0 * cs
            a2 = 1.0 - alpha
        elif ftype == "Allpass":
            freq = conf["freq"]
            q = conf["q"]
            omega = 2.0 * math.pi * freq / fs
            sn = math.sin(omega)
            cs = math.cos(omega)
            alpha = sn / (2.0 * q)
            b0 = 1.0 - alpha
            b1 = -2.0 * cs
            b2 = 1.0 + alpha
            a0 = 1.0 + alpha
            a1 = -2.0 * cs
            a2 = 1.0 - alpha
        elif ftype == "AllpassFO":
            freq = conf["freq"]
            omega = 2.0 * math.pi * freq / fs
            tn = math.tan(omega / 2.0)
            alpha = (tn + 1.0) / (tn - 1.0)
            b0 = 1.0
            b1 = alpha
            b2 = 0.0
            a0 = alpha
            a1 = 1.0
            a2 = 0.0
        elif ftype == "LinkwitzTransform":
            f0 = conf["freq_act"]
            q0 = conf["q_act"]
            qt = conf["q_target"]
            ft = conf["freq_target"]

            d0i = (2.0 * math.pi * f0) ** 2
            d1i = (2.0 * math.pi * f0) / q0
            c0i = (2.0 * math.pi * ft) ** 2
            c1i = (2.0 * math.pi * ft) / qt
            fc = (ft + f0) / 2.0

            gn = 2 * math.pi * fc / math.tan(math.pi * fc / fs)
            cci = c0i + gn * c1i + gn ** 2

            b0 = (d0i + gn * d1i + gn ** 2) / cci
            b1 = 2 * (d0i - gn ** 2) / cci
            b2 = (d0i - gn * d1i + gn ** 2) / cci
            a0 = 1.0
            a1 = 2.0 * (c0i - gn ** 2) / cci
            a2 = (c0i - gn * c1i + gn ** 2) / cci

        self.fs = fs
        self.a1 = a1 / a0
        self.a2 = a2 / a0
        self.b0 = b0 / a0
        self.b1 = b1 / a0
        self.b2 = b2 / a0

    def complex_gain(self, freq):
        zvec = [cmath.exp(1j * 2 * math.pi * f / self.fs) for f in freq]
        A = [((self.b0 + self.b1 * z ** (-1) + self.b2 * z ** (-2)) / (
            1.0 + self.a1 * z ** (-1) + self.a2 * z ** (-2))) for z in zvec]
        return freq, A

    def gain_and_phase(self, f):
        _f, Avec = self.complex_gain(f)
        gain = [20 * math.log10(abs(A)) for A in Avec]
        phase = [180 / math.pi * cmath.phase(A) for A in Avec]
        return f, gain, phase

    def is_stable(self):
        return abs(self.a2) < 1.0 and abs(self.a1) < (self.a2 + 1.0)

