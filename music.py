from imslib.audio import Audio
from imslib.mixer import Mixer
from imslib.synth import Synth
from imslib.wavegen import WaveGenerator
from imslib.wavesrc import WaveFile


# Handles everything about Audio.
#   creates the main Audio object
#   load and plays solo and bg audio tracks
#   creates audio buffers for sound-fx (miss sound)
#   functions as the clock (returns song time elapsed)
class AudioController(object):
    def __init__(self, song_path):
        super(AudioController, self).__init__()
        self.audio = Audio(2)
        self.mixer = Mixer()
        self.audio.set_generator(self.mixer)

        # song
        self.solo_track = WaveGenerator(WaveFile(song_path + "_solo.wav"))
        self.bg_track = WaveGenerator(WaveFile(song_path + "_bg.wav"))
        self.mixer.add(self.solo_track)
        self.mixer.add(self.bg_track)

        # synth
        self.synth = Synth()
        self.channel = 1
        self.synth.program(self.channel, 0, 29)
        self.mixer.add(self.synth)
        self.last_miss = None
        self.pitch = 66
        self.vel = 100

        # start paused
        self.solo_track.pause()
        self.bg_track.pause()

    # start / stop the song
    def toggle(self):
        self.solo_track.play_toggle()
        self.bg_track.play_toggle()

    # mute / unmute the solo track
    def set_mute(self, mute):
        if mute:
            self.solo_track.set_gain(0)
        else:
            self.solo_track.set_gain(1)

    # play a sound-fx (miss sound)
    def play_miss(self):
        self.synth.noteon(self.channel, self.pitch, self.vel)
        self.synth.noteon(self.channel, self.pitch+5, self.vel)
        self.synth.noteon(self.channel, self.pitch-1, self.vel)
        self.last_miss = self.get_time()

    # return current time (in seconds) of song
    def get_time(self):
        return self.bg_track.frame / 44100

    # needed to update audio
    def on_update(self):
        self.audio.on_update()

        current_time = self.get_time()
        if self.last_miss and current_time - self.last_miss > 0.1:
            self.synth.noteoff(self.channel, self.pitch)
            self.synth.noteoff(self.channel, self.pitch+5)
            self.synth.noteoff(self.channel, self.pitch-1)

    def death_callback(self):
        """
        Called when the player dies
        """
        self.set_mute(True)

    def ressurection_callback(self):
        """
        Called when the player comes back to life
        """
        self.set_mute(False)

    def correct_jump_callback(self, jump_key):
        """
        Called when the player performs a jump that's in line with the color
        """
        pass

    def incorrect_jump_callback(self, jump_key):
        """
        Called when the player does not jump correctly
        """
        self.play_miss()