#
# Intercom
# |
# +- Intercom_buffer
#    |
#    +- Intercom_bitplanes
#       |
#       +- Intercom_binaural
#
# Removes binaural redundancy. The channel 1 is substracted to the channel 0.
#
from intercom_bitplanes import Intercom_bitplanes

class Intercom_binaural(Intercom_bitplanes):

    def init(self, args):
        Intercom_bitplanes.init(self, args)
        if self.number_of_channels == 2:
            self.record_send_and_play = self.record_send_and_play_stereo
        print("removing binaural redundancy")

    # Channel 0 is a residue: channel0 -= channel1
    def record_send_and_play_stereo(self, indata, outdata, frames, time, status):
        indata[:,0] -= indata[:,1]
        self.send(indata)
        self._buffer[self.played_chunk_number % self.cells_in_buffer][:,0] += self._buffer[self.played_chunk_number % self.cells_in_buffer][:,1]
        self.play(outdata)

if __name__ == "__main__":
    intercom = Intercom_binaural()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()
