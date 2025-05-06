import json
from kivy.clock import Clock
from imslib.core import BaseWidget, run

from music import AudioController
from game import GameDisplay, PlayerController

class MainWidget(BaseWidget):
    def __init__(self, level_name, level_data_path, song_base_path, screen_manager = None):
        super(MainWidget, self).__init__()

        self.screen_manager = screen_manager
        self.level_name = level_name

        # load JSON
        with open(level_data_path, 'r') as f:
            level_data = json.load(f)

        with open(song_base_path, 'r') as f:
            midi_data = json.load(f)

        self.audio_ctrl = AudioController(midi_data)
        

        self.display = GameDisplay(level_name, level_data, self.audio_ctrl, screen_manager)
        self.player_ctrl = PlayerController(self.display, self.audio_ctrl)
        self.canvas.add(self.display)

        self.audio_started = False
        self.started= False
        self.counter_until_start = 0

        

    def on_key_down(self, keycode, modifiers):
        self.player_ctrl.on_key_down(keycode)

    def on_key_up(self, keycode):
        self.player_ctrl.on_key_up(keycode)

    def on_resize(self, win_size):
        self.display.on_resize(win_size)

    def update(self, dt):
        if not self.audio_started:
            self.audio_ctrl.start()
            self.audio_started = True
        self.display.on_update(dt)
        self.player_ctrl.on_update(dt)

    def on_update(self):
        if not self.started:
            self.counter_until_start += 1
            if self.counter_until_start > 10:
                self.started = True
                Clock.schedule_interval(self.update, 1/240.0)

        self.audio_ctrl.on_update()

if __name__ == "__main__":
    
    level_data_path = 'level_data/level_data.json'
    song_base_path = 'level_data/midi_data.json'

    run(
        MainWidget(
            level_name="TEST LEVEL",
            level_data_path = level_data_path,
            song_base_path = song_base_path,
        )
    )