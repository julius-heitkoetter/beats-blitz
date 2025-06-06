from imslib.audio import Audio
from imslib.mixer import Mixer
from imslib.synth import Synth
from imslib.wavegen import WaveGenerator
from imslib.wavesrc import WaveFile
from constants import SLICE_WIDTH, SCROLL_SPEED

from imslib.clock import Clock, SimpleTempoMap, AudioScheduler, tick_str, kTicksPerQuarter, quantize_tick_up

# Handles everything about Audio.
#   creates the main Audio fobject
#   load and plays solo and bg audio tracks
#   creates audio buffers for sound-fx (miss sound)
#   functions as the clock (returns song time elapsed)
class AudioController(object):
    def __init__(self, midi_data):
        super(AudioController, self).__init__()
        self.audio = Audio(2)
        self.synth = Synth()
       

        

        self.cmd = None
        self.off_cmd = None

        self.next_note_info = None
        
        self.midi_data = midi_data

        self.playing = False

        self.tempo_map  = SimpleTempoMap(self.midi_data["metadata"]["bpm"])
        self.sched = AudioScheduler(self.tempo_map)

        self.audio.set_generator(self.sched)
        self.sched.set_generator(self.synth)


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
        self.bass_channels  = [9]

        self.notes = midi_data.get('notes_by_tick', {})
        keys =  list(self.notes.keys())
        #go through the notes which are index by tick in string, and if off by one tick add the contents to previsous tick so it is more unified
        for tick in keys:
            tick = int(tick)
            if str(tick-1) in self.notes:
                self.notes[str(tick-1)].extend(self.notes[str(tick)])
                del self.notes[str(tick)]

        for channel_id, metadata in self.midi_data.get('channel_metadata', {}).items():
            # Only create synths for channels that are set to play
            if metadata.get('play_track', 1) == 1:
                channel = int(channel_id)
                program = metadata.get('program', 0)
                bank = 0  # Default bank

                if program == 32:
                    self.bass_channels.append(channel) #add to bass channels
                
                # Set the program (instrument sound) for this channel
                self.synth.program(channel, bank, program)
                

                
                # Store in our channel_synths dictionary
                self.channel_synths[channel] = {
                    'program': program,
                    'active_notes': set(),  # Track currently playing notes
                }
                if metadata.get('mute_track', 0): #track that can be muted/ a main track
                    self.main_channels.append(channel)
                else:
                    self.background_channels.append(channel)
            self.synth.program(9, 128, 0)
        self.change_volume(self.background_channels,0.2) #set volume of main channels to 60%
        self.change_volume(self.main_channels, 0.3) #set volume of main channels to 60%
        self.change_volume(self.bass_channels, 0.5) #set volume of main channels to 60%
    def change_volume(self, channels, volume):
        """
        Change the volume of the specified channels.
        """
        volume_number = int(volume * 127)  # Convert to MIDI volume range (0-127)
        for channel in channels:
            if channel in self.channel_synths:
                self.synth.cc(channel, 7, volume_number)  # Control Change for volume (CC 7)

    def play_note_at_tick(self, system_tick, tick):
        now = self.sched.get_tick()
        #print("playing note at tick", now, "witch code ticl", tick, "at system tick wanted ", system_tick)
        
        for notes in self.notes.get(str(tick), []):
            channel = notes['channel']
            note = notes['note']
            velocity = notes['velocity']
            length = notes['length_ticks']
            #print("start tick is, ", notes["start_tick"], "and slice is ", notes["slice"])
            self.synth.noteon(channel, note, velocity)
            self.channel_synths[channel]['active_notes'].add(note)
            note_off_tick = now + length * 10
                
            self.off_cmd = self.sched.post_at_tick(self._noteoff, note_off_tick, (channel, note))
        #play next tick index in dictionary
        
        #fidn the next item in the dictionary efficiently
        next_tick = min((int(t) for t in self.notes.keys() if int(t) > tick), default=None)
        #print(next_tick)
        if next_tick is not None:
            self.next_note_info = [now+(next_tick-tick)*10,next_tick]
            self.cmd = self.sched.post_at_tick(self.play_note_at_tick, self.next_note_info[0],self.next_note_info[1])

    def _noteoff(self, tick, args):
        """
        Called to turn off a note. 
        """
        #print("note off")
        channel, note = args
        if channel in self.channel_synths:
            self.synth.noteoff(channel, note)
            self.channel_synths[channel]['active_notes'].discard(note)

      
    def slice_to_time(self, slice_num):
        """
        Converts a slice number to time in seconds.
        """
        return slice_num * SLICE_WIDTH / SCROLL_SPEED
    
    def start(self):
        if self.playing:
            return
        #print("Starting audio ... ")
        # find the tick of the next beat, and make it "beat aligned"
        now = self.sched.get_tick()
       
        first_tick = min(int(tick) for tick in self.notes.keys())
        next_beat = now + first_tick # get first tick group
        #print(now, next_beat)
        # now, post the _noteon function (and remember this command)
        
        self.cmd = self.sched.post_at_tick(self.play_note_at_tick, next_beat, first_tick )

        self.playing = True
        # TODO set program and start playing.

    def stop(self):

        self.sched.cancel(self.cmd)
        self.__init__(self.midi_data) #reset the audio controller

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
        self.change_volume(self.main_channels, 0.05) #mute main channels
        self.change_volume(self.background_channels, 0.2) #keep background
        self.change_volume(self.bass_channels, 0.2)

    def ressurection_callback(self):
        """
        Called when the player comes back to life
        """
        self.change_volume(self.main_channels, 0.3) #mute main channels
        self.change_volume(self.background_channels, 0.2) #mute main channels
        self.change_volume(self.bass_channels, 0.5)

    def correct_jump_callback(self, jump_key, slice_num):
        """
        Called when the player performs a jump that's in line with the color
        """
        tick_epsilon = 100
        print("CORRECT JUMP", jump_key, slice_num)
        self.change_volume(self.main_channels, 0.3)
        self.change_volume(self.background_channels, 0.2)
        self.change_volume(self.bass_channels, 0.5)
        now = self.sched.get_tick()
        if(self.next_note_info is not None):
            if self.next_note_info[0] - now < tick_epsilon:
                #jumping to next note#
                self.sched.cancel(self.cmd)
                self.play_note_at_tick(now, self.next_note_info[1])

    def incorrect_jump_callback(self, jump_key, tick_num):
        """
        Called when the player does not jump correctly
        """
        self.play_miss()
        self.change_volume(self.main_channels, 0.15)
        self.change_volume(self.background_channels, 0.2)
        self.change_volume(self.bass_channels, 0.3)
        