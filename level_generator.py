import argparse
import json
import numpy as np
from mido import MidiFile, MidiTrack, Message

from constants import SLICE_WIDTH, SCROLL_SPEED

class LevelGenerator:
    def __init__(self, midi_file_path):
        """Initialize the level generator with a MIDI file."""
        self.midi_file = MidiFile(midi_file_path)
        self.tempo = 397350  # default tempo (microseconds per beat)
        self.ticks_per_beat = self.midi_file.ticks_per_beat
        
        # Platform type mappings by octave
        # Each array index corresponds to an octave (C0, C1, etc.)
        self.platform_mappings = {
            # C notes (12, 24, 36, etc.)
            0: {"type": "empty", "color": [1, 0, 0], "height": 2},                        # C0 - Basic platform
            1: {"type": "floatingSquare", "color": [1, 0, 0], "height": 2},    # C1 - Red platform
            2: {"type": "floatingSquare", "color": [0, 1, 0], "height": 2},    # C2 - Green platform
            3: {"type": "floatingSquare", "color": [0, 0, 1], "height": 2},    # C3 - Blue platform
            4: {"type": "floatingSquare", "height": 1, "color": [1, 0, 0]},           # C4 - White tower
            5: {"type": "tower", "height": 1, "color": [1, 0, 0]},  # C5 - Red tower
            6: {"type": "tower", "height": 1, "color": [0, 0, 1]},  # C6 - Blue tower
            7: {"type": "tower", "height": 1, "color": [0, 1, 0]},  # C7 - Green tower
            8: {"type": "towerWithSpikes", "height": 2},           # C8 - Tower with spikes
            9: {"type": "spikes"},                                  # C9 - Spikes
            10: {"type": "floatingSquare","color": [0, 1, 0], "height": 2},            # C10 - Floating square
            11: {"type": "floatingSquareWithSpikes", "height": 2, "spikesOnTop": True}  # C11 - Floating spikes
        }
        
    def _ticks_to_seconds(self, ticks, tempo=None):
        """Convert MIDI ticks to seconds based on tempo."""
        if tempo is None:
            tempo = self.tempo
        return ticks * (tempo / 1000000.0) / self.ticks_per_beat
    
    def time_to_slice(self, time):
        """Converts time in seconds to a slice number (rounded)."""
        return round(time * SCROLL_SPEED / SLICE_WIDTH)
    
    def slice_to_time(self, slice_num):
        """Converts a slice number to time in seconds."""
        return slice_num * SLICE_WIDTH / SCROLL_SPEED
    
    def extract_midi_data(self):
        """Extract MIDI data organized by channel with note durations."""
        all_notes = []  # Will be used to find all note-on and note-off events
        tempo_changes = []
        current_tempo = self.tempo
        
        # Map to store notes by channel
        channel_notes = {}
        # Store program changes by channel
        channel_programs = {}
        
        # First pass: get all note events and program changes
        for track_idx, track in enumerate(self.midi_file.tracks):
            track_tick = 0
            
            for msg in track:
                track_tick += msg.time
                
                # Track tempo changes
                if msg.type == 'set_tempo':
                    current_tempo = msg.tempo
                    tempo_changes.append({
                        'tick': track_tick,
                        'tempo': msg.tempo,
                        'time': self._ticks_to_seconds(track_tick, current_tempo)
                    })
                    self.tempo = current_tempo
                
                # Track program changes (instrument sounds)
                elif msg.type == 'program_change':
                    if msg.channel not in channel_programs:
                        channel_programs[msg.channel] = []
                    
                    channel_programs[msg.channel].append({
                        'tick': track_tick,
                        'program': msg.program,
                        'time': self._ticks_to_seconds(track_tick, current_tempo)
                    })
                
                # Track note on events
                elif msg.type == 'note_on':
                    note_event = {
                        'tick': track_tick,
                        'time': self._ticks_to_seconds(track_tick, current_tempo),
                        'note': msg.note,
                        'velocity': msg.velocity,
                        'channel': msg.channel,
                        'track': track_idx,
                        'type': 'on' if msg.velocity > 0 else 'off'
                    }
                    all_notes.append(note_event)
                
                # Track note off events
                elif msg.type == 'note_off':
                    note_event = {
                        'tick': track_tick,
                        'time': self._ticks_to_seconds(track_tick, current_tempo),
                        'note': msg.note,
                        'velocity': 0,
                        'channel': msg.channel,
                        'track': track_idx,
                        'type': 'off'
                    }
                    all_notes.append(note_event)
        
        # Sort all notes by tick time
        all_notes.sort(key=lambda x: (x['tick'], 0 if x['type'] == 'on' else 1))
        
        # Second pass: match note-on and note-off events to calculate durations
        active_notes = {}  # Format: {(channel, note): note_on_event}
        
        for event in all_notes:
            channel = event['channel']
            note = event['note']
            key = (channel, note)
            
            if channel not in channel_notes:
                channel_notes[channel] = []
            
            if event['type'] == 'on' and event['velocity'] > 0:
                # Note on event - add to active notes
                active_notes[key] = event
            
            elif event['type'] == 'off' or (event['type'] == 'on' and event['velocity'] == 0):
                # Note off event - check if we have a matching note on
                if key in active_notes:
                    note_on = active_notes[key]
                    note_length_ticks = event['tick'] - note_on['tick']
                    note_length_time = event['time'] - note_on['time']
                    
                    # Skip very short notes (likely errors or artifacts)
                    if note_length_ticks > 0:
                        # Create a complete note event
                        complete_note = {
                            'start_tick': note_on['tick'],
                            'start_time': note_on['time'],
                            'end_tick': event['tick'],
                            'end_time': event['time'],
                            'length_ticks': note_length_ticks,
                            'length_time': note_length_time,
                            'note': note,
                            'velocity': note_on['velocity'],
                            'slice': self.time_to_slice(note_on['time'])
                        }
                        channel_notes[channel].append(complete_note)
                    
                    # Remove from active notes
                    del active_notes[key]
        
        # Set default instrument programs for channels if not found
        for channel in range(16):
            if channel not in channel_programs:
                channel_programs[channel] = [{'program': 0}]  # Default to program 0
        
        # Create channel metadata
        channel_metadata = {}
        for channel, programs in channel_programs.items():
            # Get the last program change for this channel (or default to 0)
            last_program = programs[-1]['program'] if programs else 0
            channel_metadata[str(channel)] = {
                'program': last_program,
                'mute_track': 0,  # Default to not muted
                'play_track': 1   # Default to play track
            }
        
        return {
            'channel_notes': channel_notes,
            'channel_metadata': channel_metadata,
            'tempo_changes': tempo_changes
        }

    def get_platform_type(self, midi_note, velocity):
        """Get platform type based on MIDI note and velocity."""
        # Get octave (C0, C1, etc.) by dividing by 12
        octave = midi_note // 12
        
        # Get the default platform for this octave
        if octave in self.platform_mappings:
            platform = self.platform_mappings[octave].copy()
        else:
            # Default to empty platform if octave is out of range
            platform = {"type": "empty"}
        
        # Scale height based on velocity - divide by 16 as requested
        # This will give a range of 1-8 for velocity range 1-128
        if 'height' in platform:
            height_scale = max(1, velocity // 16)
            platform['height'] = height_scale
            
        # Add color based on note within octave
        note_in_octave = midi_note % 12
        
        # Different notes within octave can have different colors
        if 'color' not in platform:
            if note_in_octave == 0:  # C note - keep default color
                pass
            elif note_in_octave == 4:  # E note - Red
                platform['color'] = [1, 0, 0]
            elif note_in_octave == 7:  # G note - Green
                platform['color'] = [0, 1, 0]
            elif note_in_octave == 9:  # A note - Blue
                platform['color'] = [0, 0, 1]
                
        return platform

    def generate_level_data(self, platform_channel=None):
        """Generate level data from MIDI notes."""
        midi_data = self.extract_midi_data()
        level_data = {}
        
        # If no platform channel specified, use the last channel that has notes
        if platform_channel is None:
            max_channel = 0
            for channel in midi_data['channel_notes'].keys():
                max_channel = max(max_channel, int(channel))
            platform_channel = max_channel
        
        print(f"Using channel {platform_channel} for platform data")
        
        # Check if the platform channel exists in our data
        if platform_channel not in midi_data['channel_notes']:
            print(f"Warning: Channel {platform_channel} not found in MIDI data. No platforms generated.")
            return level_data, midi_data
        
        # Create level data for each note in the platform channel
        for note in midi_data['channel_notes'][platform_channel]:
            slice_num = note['slice']
            
            # Get platform type based on MIDI note
            platform_type = self.get_platform_type(note['note'], note['velocity'])
            
            # Add to level data (only if slice doesn't already have something)
            if str(slice_num) not in level_data:
                level_data[str(slice_num)] = platform_type
        
        return level_data, midi_data

def generate_files(midi_file, level_output, midi_output, platform_channel=None):
    """Generate level_data.json and midi_data.json from a MIDI file."""
    generator = LevelGenerator(midi_file)
    level_data, midi_data = generator.generate_level_data(platform_channel)
    
    # If no platform channel was specified, use the one that was determined in generate_level_data
    if platform_channel is None:
        # Find the last channel with notes
        max_channel = 0
        for channel in midi_data['channel_notes'].keys():
            max_channel = max(max_channel, int(channel))
        platform_channel = max_channel
    
    # Save level data
    with open(level_output, 'w') as f:
        json.dump(level_data, f, indent=2)
    
    # Save MIDI data - reorganize to be tick-based instead of channel-based
    with open(midi_output, 'w') as f:
        # Collect all notes from all channels except the platform channel
        all_notes = []
        for channel, notes in midi_data['channel_notes'].items():
            channel_num = int(channel)
            # Skip the platform channel that's used for level data
            if channel_num != platform_channel:
                for note in notes:
                    # Add channel to each note
                    note_with_channel = note.copy()
                    note_with_channel['channel'] = channel_num
                    all_notes.append(note_with_channel)
        
        # Sort by tick
        all_notes.sort(key=lambda x: x['start_tick'])
        
        # Group by tick
        notes_by_tick = {}
        for note in all_notes:
            tick = str(note['start_tick'])
            if tick not in notes_by_tick:
                notes_by_tick[tick] = []
            notes_by_tick[tick].append(note)
        
        # Calculate BPM from tempo
        initial_tempo = midi_data['tempo_changes'][0]['tempo'] if midi_data['tempo_changes'] else 500000
        initial_bpm = 60000000 / initial_tempo
        
        midi_output_data = {
            'notes_by_tick': notes_by_tick,
            'channel_metadata': midi_data['channel_metadata'],
            'tempo_changes': midi_data['tempo_changes'],
            'metadata': {
                'ticks_per_beat': generator.midi_file.ticks_per_beat,
                'type': generator.midi_file.type,
                'length_seconds': generator.midi_file.length,
                'track_count': len(generator.midi_file.tracks),
                'bpm': initial_bpm  # Add BPM information
            }
        }
        json.dump(midi_output_data, f, indent=2)
    
    print(f"Generated {level_output} with {len(level_data)} platform slices")
    print(f"Generated {midi_output} with data organized by MIDI ticks (excluding platform channel {platform_channel})")

def main():
    parser = argparse.ArgumentParser(description='Generate Beat Blitz level from a MIDI file')
    parser.add_argument('--midi_file', help='Path to the MIDI file')
    parser.add_argument('--level_output', default='level_data.json', help='Output level data JSON file path')
    parser.add_argument('--midi_output', default='midi_data.json', help='Output MIDI data JSON file path')
    parser.add_argument('--channel', type=int, help='MIDI channel to use for platforms (default: last channel)')
    
    args = parser.parse_args()
    
    generate_files(args.midi_file, args.level_output, args.midi_output, args.channel)

if __name__ == "__main__":
    main()