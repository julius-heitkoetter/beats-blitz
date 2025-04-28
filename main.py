import json
from kivy.clock import Clock
from imslib.core import BaseWidget, run

from music import AudioController
from game import GameDisplay, PlayerController

class MainWidget(BaseWidget):
    def __init__(self, level_data_path, song_base_path):
        super(MainWidget, self).__init__()

        # load JSON
        with open(level_data_path, 'r') as f:
            level_data = json.load(f)

        self.audio_ctrl = AudioController(song_base_path)
        self.audio_ctrl.toggle()

        self.display = GameDisplay(level_data, self.audio_ctrl)
        self.player_ctrl = PlayerController(self.display, self.audio_ctrl)
        self.canvas.add(self.display)

        Clock.schedule_interval(self.update, 1/60.0)

    def on_key_down(self, keycode, modifiers):
        self.player_ctrl.on_key_down(keycode)

    def on_key_up(self, keycode):
        self.player_ctrl.on_key_up(keycode)

    def on_resize(self, win_size):
        pass

    def update(self, dt):
        self.display.on_update(dt)
        self.player_ctrl.on_update(dt)
        self.audio_ctrl.on_update()

if __name__ == "__main__":
    
    level_data_path = 'level_data/demo_level_2.json'
    song_base_path = 'level_data/SmokeOnTheWater'

    run(
        MainWidget(
            level_data_path = level_data_path,
            song_base_path = song_base_path,
        )
    )