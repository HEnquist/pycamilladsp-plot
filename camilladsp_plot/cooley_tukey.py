# Adapted from https://jeremykun.com/2012/07/18/the-fast-fourier-transform/
import cmath
import math


def omega(p, q):
   return cmath.exp((2.0 * cmath.pi * 1j * q) / p)

OMEGA20 = omega(2, 0)
OMEGA40 = omega(4, 0)
OMEGA41 = omega(4, -1)

TWIDDLES = {}

def get_twiddles(n):
   if n in TWIDDLES:
      return TWIDDLES[n]
   else:
      tw = [omega(n, -m) for m in range(int(n / 2))]
      TWIDDLES[n] = tw
      return tw


def _fft4(signal):
   Fe0 = signal[0] + OMEGA20 * signal[2]
   Fe1 = signal[0] - OMEGA20 * signal[2]
   Fo0 = signal[1] + OMEGA20 * signal[3]
   Fo1 = signal[1] - OMEGA20 * signal[3]

   return [
      Fe0 + OMEGA40 * Fo0,
      Fe1 + OMEGA41 * Fo1,
      Fe0 - OMEGA40 * Fo0,
      Fe1 - OMEGA41 * Fo1,
   ]


def _fft(signal):
   n = len(signal)
   if n == 4:
      return _fft4(signal)
   elif n == 1:
      return signal
   else:
      Feven = _fft(signal[0::2])
      Fodd = _fft(signal[1::2])
      tw = get_twiddles(n)
      combined = [fe + t * fo for fe, fo, t in zip(Feven, Fodd, tw)] + [
         fe - t * fo for fe, fo, t in zip(Feven, Fodd, tw)
      ]
      return combined


def fft(signal):
   orig_len = len(signal)
   fft_len = 2 ** (math.ceil(math.log2(orig_len)))
   padding = [0.0 for _n in range(fft_len - orig_len)]
   signal.extend(padding)
   fftsig = _fft(signal)
   return fftsig


if __name__ == "__main__":
   # testing area, compare to numpy fft
   import numpy as np
   import numpy.fft as npfft
   import time

   data_test = [n for n in range(16)]
   pyf = fft(data_test)
   npf = npfft.fft(data_test)

   for n in range(len(pyf)):
      print(abs(pyf[n] - npf[n]))

   data = [0.0 for n in range(2 ** 16)]

   start = time.time()
   _f = npfft.fft(data)
   print(f"numpy took {(time.time()-start)*1000} ms")
   start = time.time()
   _f = fft(data)
   print(f"fft took {(time.time()-start)*1000} ms")

