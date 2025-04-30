from mido import MidiFile

# Load the MIDI file
midi_file = MidiFile('level_data\loz-la-overworld.mid')

# Iterate through the tracks and messages
for i, track in enumerate(midi_file.tracks):
    print(f"Track {i}: {track.name}")
    for message in track:
        print(message)