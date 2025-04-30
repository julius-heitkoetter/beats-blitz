from imslib.audio import Audio
from imslib.mixer import Mixer
from imslib.synth import Synth
from imslib.wavegen import WaveGenerator
from imslib.wavesrc import WaveFile
from constants import SLICE_WIDTH, SCROLL_SPEED

from imslib.clock import Clock, SimpleTempoMap, AudioScheduler, tick_str, kTicksPerQuarter, quantize_tick_up

# Handles everything about Audio.
#   creates the main Audio object
#   load and plays solo and bg audio tracks
#   creates audio buffers for sound-fx (miss sound)
#   functions as the clock (returns song time elapsed)
class AudioController(object):
    def __init__(self, midi_data):
        super(AudioController, self).__init__()
        self.audio = Audio(2)
        self.mixer = Mixer()
       

        self.tempo_map  = SimpleTempoMap(120)
        self.sched = AudioScheduler(self.tempo_map)

        self.audio.set_generator(self.sched)
        self.sched.set_generator(self.mixer)

        self.cmd = None
        
        self.midi_data = midi_data

        self.playing = False


        """#get sound effects from 
        self.ressurection_sound = WaveGenerator(WaveFile(sound_effect_path + "/ressurection.wav"))
        self.death_sound = WaveGenerator(WaveFile(sound_effect_path + "/death.wav"))
        self.incorrect_jump_sound = WaveGenerator(WaveFile(sound_effect_path + "/incorrect_jump.wav"))

        #add tracks to the mixer
        self.mixer.add(self.ressurection_sound)
        self.mixer.add(self.death_sound)
        self.mixer.add(self.incorrect_jump_sound)

        #pausing all tracks before
        self.ressurection_sound.pause()
        self.death_sound.pause()
        self.incorrect_jump_sound.pause()"""


        self.main_channels = []
        self.background_channels = []
        self.channel_synths = {}

        self.notes = midi_data.get('notes_by_tick', {})

        for channel_id, metadata in self.midi_data.get('channel_metadata', {}).items():
            # Only create synths for channels that are set to play
            if metadata.get('play_track', 1) == 1:
                channel = int(channel_id)
                synth = Synth()
                program = metadata.get('program', 0)
                bank = 0  # Default bank
                
                # Set the program (instrument sound) for this channel
                synth.program(channel, bank, program)
                
                # Add to mixer
                self.mixer.add(synth)
                
                # Store in our channel_synths dictionary
                self.channel_synths[channel] = {
                    'synth': synth,
                    'program': program,
                    'active_notes': set(),  # Track currently playing notes
                }
                if metadata.get('mute_track', 0): #track that can be muted/ a main track
                    self.main_channels.append(channel)
                else:
                    self.background_channels.append(channel)
        self.change_volume(self.background_channels, 0.6) #set volume of main channels to 60%

    def change_volume(self, channels, volume):
        """
        Change the volume of the specified channels.
        """
        volume_number = int(volume * 127)  # Convert to MIDI volume range (0-127)
        for channel in channels:
            if channel in self.channel_synths:
                synth = self.channel_synths[channel]['synth']
                synth.cc(channel, 7, volume_number)  # Control Change for volume (CC 7)

    def play_note_at_tick(self, system_tick, tick):
        print("playing note at tick")
        now = self.sched.get_tick()
        for notes in self.notes.get(tick, []):
            channel = notes['channel']
            note = notes['note']
            velocity = notes['velocity']
            length = notes['length_ticks']

            if channel in self.channel_synths:
                synth = self.channel_synths[channel]['synth']
                synth.note_on(channel, note, velocity)
                self.channel_synths[channel]['active_notes'].add(note)
                print("playing notes at tick: ", tick)

                
                self.cmd = self.sched.post_at_tick(self._noteoff, now + length, channel, note)
        #play next tick index in dictionary
        
        #fidn the next item in the dictionary efficiently
        next_tick = min((int(tick) for tick in self.notes.keys() if tick > tick), default=None)
        if next_tick is not None:
            self.cmd = self.sched.post_at_tick(self.play_note_at_tick, now+next_tick,next_tick)

    def _noteoff(self, tick, channel, note):
        """
        Called to turn off a note.
        """
        if channel in self.channel_synths:
            synth = self.channel_synths[channel]['synth']
            synth.note_off(channel, note)
            self.channel_synths[channel]['active_notes'].discard(note)

      
    def slice_to_time(self, slice_num):
        """
        Converts a slice number to time in seconds.
        """
        return slice_num * SLICE_WIDTH / SCROLL_SPEED
    
    def start(self):
        if self.playing:
            return
        print("Starting audio ... ")
        # find the tick of the next beat, and make it "beat aligned"
        now = self.sched.get_tick()
       
        first_tick = min(int(tick) for tick in self.notes.keys()) * 10
        next_beat = now + first_tick # get first tick group
        print(now, next_beat)
        # now, post the _noteon function (and remember this command)
        
        self.cmd = self.sched.post_at_tick(self.play_note_at_tick, next_beat, first_tick )

        self.playing = True
        # TODO set program and start playing.

    def stop(self):

        self.sched.cancel(self.cmd)
        self.cmd = None
        
        self.playing = False

    # start / stop the song
    def toggle(self):
        print("toggled")
        if self.playing:
            self.stop()
        else:
            self.start()


    # play a sound-fx (miss sound)
    def play_miss(self):
        return

    # return current time (in seconds) of song
    def get_time(self):
        return self.sched.get_time()

    # needed to update audio
    def on_update(self):
        self.audio.on_update()




    def death_callback(self):
        """
        Called when the player dies
        """
        self.change_volume(self.main_channels, 0.0) #mute main channels
        self.change_volume(self.background_channels, 0.4) #mute main channels

    def ressurection_callback(self):
        """
        Called when the player comes back to life
        """
        self.change_volume(self.main_channels, 1) #mute main channels
        self.change_volume(self.background_channels, 0.6) #mute main channels

    def correct_jump_callback(self, jump_key, tick_num):
        """
        Called when the player performs a jump that's in line with the color
        """
        print("CORRECT JUMP", jump_key, tick_num)

    def incorrect_jump_callback(self, jump_key, tick_num):
        """
        Called when the player does not jump correctly
        """
        self.play_miss()