import json
from kivy.graphics.instructions import InstructionGroup
from kivy.graphics import Color, Line, Rectangle
from kivy.clock import Clock
from kivy.core.window import Window
from imslib.gfxutil import topleft_label
from imslib.core import BaseWidget

from obstacles import obstacle_factory
from constants import GROUND_HEIGHT, GRAVITY, COLOR_MAP, SCROLL_SPEED, SLICE_WIDTH, JUMP_STRENGTH

# ---------------------------------------------------------
#  GAME DISPLAY
# ---------------------------------------------------------
class GameDisplay(InstructionGroup):
    """
    - Loads obstacles from JSON
    - Maintains player motion (x,y) with gravity
    - Distinguishes side/spike collision => death vs.
      top collision => stand or bottom collision => head-bump
    - Only allows jumps when on ground or on top of an obstacle
    """
    def __init__(self, level_data):
        super(GameDisplay, self).__init__()

        # load obstacles
        self.obstacles = []
        for k, val in level_data.items():
            slice_idx = int(k)
            obj = obstacle_factory(slice_idx, val)
            self.obstacles.append(obj)
        self.obstacles.sort(key=lambda o: o.slice_idx)

        for o in self.obstacles:
            self.add(o)

        self.scroll_x = 0

        # player
        self.player_size = 40
        self.player_x = 200
        self.player_y = GROUND_HEIGHT
        self.player_vel_y = 0
        self.is_on_something = True  # starts on ground
        self.player_color_key = 1
        c = COLOR_MAP[self.player_color_key]
        self.player_color = Color(*c)
        self.player_rect  = Rectangle(pos=(self.player_x,self.player_y),
                                      size=(self.player_size,self.player_size))
        self.add(self.player_color)
        self.add(self.player_rect)

        # floor
        w, h = Window.size
        self.floor = Rectangle(pos = (0, 0),
                                size = (w, GROUND_HEIGHT))
        self.floor_color = Color((1,1,1))
        self.add(self.floor_color)
        self.add(self.floor)

        # dead state
        self.dead = False

        # scoring
        self.score  = 0
        self.streak = 0

    def update_player_color(self, color_key):
        self.player_color_key = color_key
        c = COLOR_MAP.get(color_key, (1,1,1))
        self.player_color.r, self.player_color.g, self.player_color.b = c

    def scroll_world(self, dt):
        self.scroll_x += SCROLL_SPEED * dt
        for o in self.obstacles:
            slice_left_x = o.slice_idx * SLICE_WIDTH - self.scroll_x
            o.set_position(slice_left_x, GROUND_HEIGHT)

    def on_update(self, dt):
        if self.dead:
            self.scroll_world(dt)
            return

        # scroll
        self.scroll_world(dt)

        # apply gravity
        self.player_vel_y += GRAVITY * dt
        old_y = self.player_y
        self.player_y += self.player_vel_y * dt

        # handle floor
        if self.player_y < GROUND_HEIGHT:
            self.player_y = GROUND_HEIGHT
            self.player_vel_y = 0
            self.is_on_something = True
        else:
            self.is_on_something = False  # We'll set to True if we land on top of an obstacle

        # move the player
        self.player_rect.pos = (self.player_x, self.player_y)

        # collision check
        self.check_collisions(old_y)

    def check_collisions(self, old_y):
        px, py = self.player_x, self.player_y
        psize  = self.player_size
        vy     = self.player_vel_y

        for obs in self.obstacles:
            result = obs.check_collision(px, py, psize, vy)
            if result.ctype == 'spike' or result.ctype == 'side':
                # immediate death
                self.died()
                return
            elif result.ctype == 'top':
                # land on top => set player bottom to that top
                self.player_y = result.topY
                self.player_vel_y = 0
                self.player_rect.pos = (self.player_x, self.player_y)
                self.is_on_something = True
            elif result.ctype == 'bottom':
                # bump head => push player down a bit
                # e.g., set the player's top to obstacle bottom
                # (which means player's bottom = obstacle bottom - psize)
                new_top = result.topY
                self.player_y = new_top - psize
                self.player_vel_y = 0
                self.player_rect.pos = (self.player_x, self.player_y)
                # not "on_something" from below
            # else 'none' => do nothing

    # -- Death / Respawn stubs (if you want them) --
    def died(self):
        self.dead = True
        self.score -= 50
        self.streak = 0
        self.died_function()
        # color the player gray to indicate death
        self.player_color.r, self.player_color.g, self.player_color.b = (0.2, 0.2, 0.2)

    def died_function(self):
        print("died() function called")

    def correct_jump(self):
        self.score += 10
        self.streak += 1

    def incorrect_jump(self):
        self.score -= 5
        self.streak = 0

# ---------------------------------------------------------
#  PLAYER CONTROLLER
# ---------------------------------------------------------
class PlayerController(object):
    """
    - Only jumps if 'is_on_something' is true
    - Checks color correctness
    """
    def __init__(self, display):
        self.display = display

        self.key_held = None

    def on_key_down(self, keycode):
        if keycode[1] in ['1','2','3']:
            self.key_held = int(keycode[1])

    def on_key_up(self, keycode):
        print("HERE")
        if keycode[1] in ['1','2','3']:
            self.key_held = None

    def on_update(self, dt):

        #print(self.key_held)

        # Can do nothing if dead
        if self.display.dead:
            return

        if self.key_held:
            self.attempt_jump(self.key_held)

    def attempt_jump(self, color_key):
        # can only jump if on something
        if not self.display.is_on_something:
            return

        # apply upward velocity
        self.display.player_vel_y = JUMP_STRENGTH
        # TODO: add 180 degree jump rotation

        # check color correctness
        if color_key == self.display.player_color_key:
            self.display.correct_jump()
        else:
            self.display.incorrect_jump()

        # update color to the newly pressed key
        self.display.update_player_color(color_key)

# ---------------------------------------------------------
#  MAIN WIDGET
# ---------------------------------------------------------

class MainWidget(BaseWidget):
    def __init__(self, level_data_path = 'level_data/demo_level_1.json'):
        super(MainWidget, self).__init__()

        # load JSON
        with open(level_data_path, 'r') as f:
            level_data = json.load(f)

        self.display = GameDisplay(level_data)
        self.player_ctrl = PlayerController(self.display)
        self.canvas.add(self.display)

        self.info = topleft_label()
        self.add_widget(self.info)

        Clock.schedule_interval(self.update, 1/60.0)

    def on_key_down(self, keycode, modifiers):
        self.player_ctrl.on_key_down(keycode)

    def on_key_up(self, keycode):
        print("HERE2")
        self.player_ctrl.on_key_up(keycode)

    def on_resize(self, win_size):
        pass

    def update(self, dt):
        self.display.on_update(dt)
        self.player_ctrl.on_update(dt)
        self.info.text = f"Score: {self.display.score}\nStreak: {self.display.streak}"