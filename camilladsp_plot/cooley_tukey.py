# Adapted from https://jeremykun.com/2012/07/18/the-fast-fourier-transform/
import cmath
import math

def omega(p, q):
   return cmath.exp((2.0 * cmath.pi * 1j * q) / p)

def _fft(signal):
   n = len(signal)
   if n == 1:
      return signal
   else:
      Feven = _fft([signal[i] for i in range(0, n, 2)])
      Fodd = _fft([signal[i] for i in range(1, n, 2)])
 
      combined = [0] * n
      for m in range(int(n/2)):
         combined[m] = Feven[m] + omega(n, -m) * Fodd[m]
         combined[m + int(n/2)] = Feven[m] - omega(n, -m) * Fodd[m]
 
      return combined

def fft(signal):
   orig_len = len(signal)
   fft_len = 2**(math.ceil(math.log2(orig_len)))
   for _n in range(fft_len-orig_len):
      signal.append(0.0)
   fftsig = _fft(signal)
   return fftsig