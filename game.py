import json
from kivy.graphics.instructions import InstructionGroup
from kivy.graphics import Color, Line, Rectangle
from kivy.core.window import Window

from obstacles import obstacle_factory
from constants import GROUND_HEIGHT, GRAVITY, COLOR_MAP, SCROLL_SPEED, SLICE_WIDTH, JUMP_STRENGTH, PLAYER_DEATH_TIMEOUT

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
    def __init__(self, level_name, level_data, audio, screen_manager):
        super(GameDisplay, self).__init__()

        self.level_name = level_name

        self.audio = audio
        self.screen_manager = screen_manager

        # floor
        w, h = Window.size
        self.floor = Rectangle(pos = (0, 0),
                                size = (w, GROUND_HEIGHT))
        self.floor_color = Color((0.5, 0.5, 0.5))
        self.add(self.floor_color)
        self.add(self.floor)

        # load obstacles
        self.obstacles = []
        for k, val in level_data.items():
            slice_idx = int(k)
            obj = obstacle_factory(slice_idx, val)
            self.obstacles.append(obj)
        self.obstacles.sort(key=lambda o: o.slice_idx)
        self.visible_obstacles = []

        #for o in self.obstacles:
            #self.add(o)

        self.scroll_x = 0

        # player
        self.player_size = 40
        self.player_x = 200
        self.player_y = GROUND_HEIGHT
        self.player_vel_y = 0
        self.is_on_something = True  # starts on ground
        self.color_under_player = None # starts with no color under the player
        self.player_color_key = 1
        c = COLOR_MAP[self.player_color_key]
        self.player_color = Color(*c)
        self.player_rect  = Rectangle(pos=(self.player_x,self.player_y),
                                      size=(self.player_size,self.player_size))
        self.add(self.player_color)
        self.add(self.player_rect)

        # dead state
        self.dead = False
        self.time_since_last_death = 0

        # end of level state
        self.level_has_ended = False

        # scoring
        self.score  = 0
        self.streak = 0
    
    def on_resize(self, win_size):
        w, _ = win_size                 # height change does not affect ground
        self.floor.size = (w, GROUND_HEIGHT)   # stretch / shrink floor bar
        # redraw player & obstacles where they *would* be at the current scroll
        # (dt = 0 → no time advance, just recompute positions)
        self.scroll_world(0)
        self.player_rect.pos = (self.player_x, self.player_y)

    def update_player_color(self, color_key):
        self.player_color_key = color_key
        c = COLOR_MAP.get(color_key, (0.5, 0.5, 0.5))
        self.player_color.r, self.player_color.g, self.player_color.b = c

    def scroll_world(self, dt):
        self.scroll_x += SCROLL_SPEED * dt
        for i, o in enumerate(self.obstacles):
            slice_left_x = o.slice_idx * SLICE_WIDTH - self.scroll_x
            #print("CuRRENT SLICE, ", self.scroll_x/SLICE_WIDTH)
            visible = -SLICE_WIDTH < slice_left_x < Window.width + SLICE_WIDTH
            if(visible):
                o.set_position(slice_left_x, GROUND_HEIGHT)
                if(o not in self.children):
                    self.add(o)
                    self.visible_obstacles.append(o)
                
                
            elif not visible and o in self.children:
                self.remove(o)
                self.visible_obstacles.remove(o)
  
            

    def on_update(self, dt):
        if self.level_has_ended:
            return

        # Check if player should be ressurected
        self.time_since_last_death += dt
        if self.dead and self.time_since_last_death > PLAYER_DEATH_TIMEOUT:
            self.ressurected()

        if self.dead:
            self.scroll_world(dt)
            self.player_rect.pos = (self.player_x, self.player_y)
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

        # ─────────────── level‑complete test ───────────────
        # Last obstacle's *right* edge in world‑space
        last_edge = (self.obstacles[-1].slice_idx + 1) * SLICE_WIDTH
        # Player’s front edge position in world‑space
        player_world_x = self.scroll_x + self.player_x + self.player_size
        if player_world_x >= last_edge + 500 and not self.dead and not self.level_has_ended:
            self.level_has_ended = True
            self.show_results()

    def check_collisions(self, old_y):
        px, py = self.player_x, self.player_y
        psize  = self.player_size
        vy     = self.player_vel_y

        color_under_player = None
        for obs in self.visible_obstacles:
            result = obs.check_collision(px, py, psize, vy)
            if result.ctype == 'spike' or result.ctype == 'side':
                # immediate death
                self.died()
                return True
            elif result.ctype == 'top':
                # land on top => set player bottom to that top
                self.player_y = result.topY
                self.player_vel_y = 0
                self.player_rect.pos = (self.player_x, self.player_y)
                self.is_on_something = True
                color_under_player = result.color
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

        self.color_under_player = color_under_player

        return False

    def died(self):

        # If already dead, don't do anything new
        if self.dead:
            return

        self.dead = True
        self.time_since_last_death = 0
        self.player_y = GROUND_HEIGHT
        self.score -= 10
        self.streak = 0
        self.audio.death_callback()

        # color the player gray to indicate death
        self.player_color.r, self.player_color.g, self.player_color.b = (0.2, 0.2, 0.2)

    def ressurected(self):

        if self.check_collisions(self.player_y):
            print("INFO : Can't ressurect because there is an obstacle in the way, waiting...")
            return

        self.dead = False
        self.audio.ressurection_callback()

         # color the player white to indicate back to lift
        self.player_color.r, self.player_color.g, self.player_color.b = (1, 1, 1)


    def correct_jump(self):
        self.streak += 1
        if self.streak>=3:
            self.score += 30
        else:
            self.score += 10

    def incorrect_jump(self):
        self.score -= 5
        self.streak = 0

    def show_results(self):
        """
        Callback to the app to show the results
        """
        score = self.score
        end_scr = self.screen_manager.get_screen("end")
        end_scr.load_results(self.level_name, score)
        self.screen_manager.current = "end"

# ---------------------------------------------------------
#  PLAYER CONTROLLER
# ---------------------------------------------------------
class PlayerController(object):
    """
    - Only jumps if 'is_on_something' is true
    - Checks color correctness
    """
    def __init__(self, display, audio):
        self.display = display
        self.audio = audio

        self.key_held = None

    def on_key_down(self, keycode):
        if keycode[1] in ['1','2','3']:
            self.key_held = int(keycode[1])

    def on_key_up(self, keycode):
        if keycode[1] in ['1','2','3']:
            self.key_held = None

    def on_update(self, dt):

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
        color_key_under_player = next( # maps the color of the obstacle to the color key
            (
                k for k, v in COLOR_MAP.items() 
                if list(v) == self.display.color_under_player
            ), 
        None)

        tick_num = int(self.display.scroll_x / SLICE_WIDTH)
        if color_key == color_key_under_player:
            self.display.correct_jump()
            self.audio.correct_jump_callback(color_key, tick_num )
        elif color_key_under_player is not None:
            self.display.incorrect_jump()
            self.audio.incorrect_jump_callback(color_key, tick_num)

        # update color to the newly pressed key
        self.display.update_player_color(color_key)