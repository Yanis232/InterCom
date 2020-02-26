#
# Intercom
# |
# +- Intercom_buffer
#    |
#    +- Intercom_bitplanes
#       |
#       +- Intercom_binaural
#          |
#          +- Intercom_DFC
#             |
#             +- Intercom_empty
#                |
#                +- Intercom_DWT
#
# Convert the chunks of samples intro chunks of wavelet coefficients
# (coeffs in short).
#
# The coefficients require more bitplanes than the original samples,
# but most of the energy of the samples of the original chunk tends to
# be into a small number of coefficients that are localized, usually
# in the low-frequency subbands:
#
# (supposing a chunk with 1024 samples)
#
# Amplitude
#     |       +                      *
#     |   *     *                  *
#     | *        *                *
#     |*          *             *
#     |             *       *
#     |                 *
#     +------------------------------- Time
#     0                  ^        1023 
#                |       |       
#               DWT  Inverse DWT 
#                |       |
#                v
# Amplitude
#     |*
#     |
#     | *
#     |  **
#     |    ****
#     |        *******
#     |               *****************
#     +++-+---+------+----------------+ Frequency
#     0                            1023
#     ^^ ^  ^     ^           ^
#     || |  |     |           |
#     || |  |     |           +--- Subband H1 (16N coeffs)
#     || |  |     +--------------- Subband H2 (8N coeffs)
#     || |  +--------------------- Subband H3 (4N coeffs)
#     || +------------------------ Subband H4 (2N coeffs)
#     |+-------------------------- Subband H5 (N coeffs)
#     +--------------------------- Subband L5 (N coeffs)
#
# (each channel must be transformed independently)
#
# This means that the most-significant bitplanes, for most of the
# chunks (this depends on the content of the chunk), should have only
# bits different of 0 in the coeffs that belongs to the low-frequency
# subbands. This will be exploited in a future issue. In a future
# issue should be implemented also a subband weighting procedure in
# order to sent first the most energetic coeffs. Notice, however, that
# these subband weights depends on the selected wavelet.
#
import struct
import numpy as np
import pywt as wt
import math
from intercom import Intercom
from intercom_empty import Intercom_empty

if __debug__:
    import sys

class Intercom_DWT(Intercom_empty):

    def init(self, args):
        Intercom_empty.init(self, args)
        self.levels = 4                  # Number of levels of the DWT
        self.wavelet = 'bior3.5'         # Wavelet Biorthogonal 3.5
        self.overlap = 4                 # Total overlap between audio chunks
        self.padding = "periodization"   # Signal extension procedure used in the DWT
        self.precision_type = np.int32   # DWT coefficients precision (storing purposes)
        self.extended_chunk_size = self.frames_per_chunk + self.overlap
        self.precision_bits = self.get_coeffs_bitplanes()
        print(self.precision_bits)
        print("using the wavelet domain")

    # Compute the number of bitplanes that the wavelet coefs require
    def get_coeffs_bitplanes(self):
        random = np.random.randint(low=-32768, high=32767, size=self.frames_per_chunk)
        coeffs = wt.wavedec(random, wavelet=self.wavelet, level=self.levels, mode=self.padding)
        arr, self.slices = wt.coeffs_to_array(coeffs)
        max = np.amax(arr)
        min = np.amin(arr)
        range = max - min
        bitplanes = int(math.floor(math.log(range)/math.log(2)))
        return bitplanes

    # After removing the binaural redundancy and before using the
    # sign-magnitude representation, the 2-channels recorded chunk is
    # transformed (each channel independently). Also, just before
    # playing the chunk, this is transformed inversely. Notice that
    # chunks in the buffer and in the network are in the wavelet
    # domain. Only the first channel is transformed (the second
    # channel is a residue chunk that when transformed should not
    # provide any coding gain).
    def record_send_and_play_stereo(self, indata, outdata, frames, time, status):
        indata[:,1] -= indata[:,0]
        indata[:,0] = self.forward_transform(indata[:,0])
        signs = indata & 0x8000
        magnitudes = abs(indata)
        indata = signs | magnitudes
        self.send(indata)
        chunk = self._buffer[self.played_chunk_number % self.cells_in_buffer]
        signs = chunk >> 15
        magnitudes = chunk & 0x7FFF
        chunk = magnitudes + magnitudes*signs*2
        self._buffer[self.played_chunk_number % self.cells_in_buffer] = chunk
        self._buffer[self.played_chunk_number % self.cells_in_buffer][:,1] += self._buffer[self.played_chunk_number % self.cells_in_buffer][:,0]
        self._buffer[self.played_chunk_number % self.cells_in_buffer] = self.inverse_transform(self._buffer[self.played_chunk_number % self.cells_in_buffer])
        self.play(outdata)
        self.received_bitplanes_per_chunk[self.played_chunk_number % self.cells_in_buffer] = 0

    def forward_transform(self, chunk):
        coeffs_in_subbands = wt.wavedec(chunk, wavelet=self.wavelet, level=self.levels, mode=self.padding)
        return wt.coeffs_to_array(coeffs_in_subbands)[0]

    def inverse_transform(self, coeffs_in_array):
        coeffs_in_subbands = wt.array_to_coeffs(coeffs_in_array, self.slices, output_format="wavedec")
        return np.around(wt.waverec(coeffs_in_subbands, wavelet=self.wavelet, mode=self.padding)).astype(self.precision_type)

if __name__ == "__main__":
    intercom = Intercom_DWT()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()
