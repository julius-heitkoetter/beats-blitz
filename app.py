from __future__ import annotations

import json
import math
import random
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, Line
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.screenmanager import Screen, ScreenManager, FadeTransition
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout

from main import MainWidget

PALETTE = {
    "bg": (0.05, 0.05, 0.08),
    "fg": (1.0, 1.0, 1.0),
    "accent_on": (0.2, 1.0, 0.65),
    "accent_off": (0.4, 0.4, 0.4),
    "accent2": (1.0, 0.35, 0.35),
}
FONT_NAME      = "fonts/UbuntuMono-B.ttf"
METADATA_FILE  = Path("level_data/level_metadata.json")

def load_levels() -> dict[str, dict]:
    if METADATA_FILE.exists():
        return json.loads(METADATA_FILE.read_text())
    raise FileNotFoundError(f"Missing {METADATA_FILE!s}")

def save_levels(levels: dict):
    METADATA_FILE.write_text(json.dumps(levels, indent=4))

class RetroLabel(Label):
    def __init__(self, **kw):
        super().__init__(font_name=FONT_NAME, color=PALETTE["fg"],
                         markup=True, **kw)

class RetroButton(Button):
    def __init__(self, **kw):
        super().__init__(font_name=FONT_NAME, background_normal="",
                         background_down="", color=(0, 0, 0), **kw)
        with self.canvas.before:
            self._col = Color(*PALETTE["accent_off"])
            self._rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._sync, pos=self._sync, disabled=self._recolor)
        self._recolor()

    def _sync(self, *_):     # keep rectangle on top of button bounds
        self._rect.size, self._rect.pos = self.size, self.pos

    def _recolor(self, *_):
        self._col.rgb = PALETTE["accent_off"] if self.disabled else PALETTE["accent_on"]

class HomeScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name="home", **kw)
        base = RelativeLayout(); self.add_widget(base)

        title = RetroLabel(text="[b]BEAT  BLITZ[/b]", font_size="64sp")
        title.size = title.texture_size; title.pos_hint = {"center_x": .5, "top": .9}
        base.add_widget(title)

        play = RetroButton(text="PLAY", size=(220, 70), size_hint=(None, None),
                   pos_hint={"center_x": .5, "center_y": .25})
        def go_to_levels(*_):
            self.manager.current = "levels"
        play.bind(on_release=go_to_levels)
        base.add_widget(play)

        with self.canvas.before:
            Color(*PALETTE["bg"]); self._bg = Rectangle(size=Window.size)
        Window.bind(size=lambda *_: self._resize_bg())   # keep bg full‑screen
        with self.canvas:
            self.polys = []; rnd = random.choice
            for _ in range(40):
                Color(*(rnd((PALETTE["accent_on"], PALETTE["accent2"])) + (0.25,)))
                self.polys.append(Line(points=self._rand_poly(), width=1.5))
        Clock.schedule_interval(self._animate, 1/30)

    def _resize_bg(self):
        self._bg.size = Window.size

    def _rand_poly(self):
        cx, cy = random.uniform(0, Window.width), random.uniform(0, Window.height)
        R = random.uniform(20, 60); sides = random.choice((3, 4)); pts = []
        for i in range(sides):
            ang = 2*math.pi*i/sides; pts += [cx+R*math.cos(ang), cy+R*math.sin(ang)]
        return pts + pts[:2]

    def _animate(self, *_):
        for ln in self.polys:
            pts = ln.points
            for i in range(0, len(pts), 2):
                pts[i] = (pts[i]+.3) % Window.width
                pts[i+1] = (pts[i+1]+.3) % Window.height
            ln.points = pts

# ─────────────────────────────── 5.  HOW-TO SCREEN ───────────────────────────────────
HOW_TO_TEXT = (
    "[b]HOW TO PLAY[/b]\n\n\n"
    "• The stage scrolls automatically – jump over obstacles like Geometry Dash.\n\n"
    "• Press number keys [b]1-3[/b]; each key emits a different colour.\n\n"
    "• Earn points by jumping [b]off of[/b] platform using the same color key\n" 
    "as the platform. White platforms accept any colour.\n\n"
    "• Wrong colour: −50 pts.  Death: −50 pts. Jumps off the correct color add 10 pts.\n\n"
)

class HowToPlayScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name="howto", **kw)
        base = RelativeLayout(); self.add_widget(base)
        label = RetroLabel(text=HOW_TO_TEXT, halign="left",
                           size_hint=(.6, .6), pos_hint={"center_x": .5, "center_y": .5})
        label.bind(size=lambda *_: label.texture_update())
        base.add_widget(label)
        back = RetroButton(text="BACK", size_hint=(None, None), size=(160, 60),
                           pos_hint={"right": .98, "y": .02})
        back.bind(on_release=self._go_to_levels)
        base.add_widget(back)
        with self.canvas.before:
            Color(*PALETTE["bg"]); Rectangle(size=Window.size)

    def _go_to_levels(self, *_):
        self.manager.current = "levels"

class LevelSelectScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name="levels", **kw)
        self.levels = App.get_running_app().levels
        root = RelativeLayout(); self.add_widget(root)

        header = RetroLabel(text="SELECT LEVEL", font_size="40sp",
                            pos_hint={"x": 0, "top": 1.35})
        root.add_widget(header)

        # scroll list
        scroll = ScrollView(size_hint=(.5, .65), pos_hint={"x": .04, "y": 0})
        self.grid = GridLayout(cols=1, size_hint_y=None, spacing=12)
        self.grid.bind(minimum_height=self.grid.setter("height")); scroll.add_widget(self.grid)
        root.add_widget(scroll)

        # info panel
        self.info = RetroLabel(text="", halign="left", valign="top",
                               size_hint=(.3, .6), pos_hint={"right": .95, "y": .25})
        self.info.bind(size=lambda *_: self.info.texture_update()); root.add_widget(self.info)

        # start & how-to buttons
        self.start_btn = RetroButton(text="START", size_hint=(.3, .1),
                                     pos_hint={"right": .95, "y": .05}, disabled=True)
        self.start_btn.bind(on_release=self._start_level); root.add_widget(self.start_btn)

        howto_btn = RetroButton(text="HOW  TO  PLAY", size_hint=(.3, .1),
                                pos_hint={"x": .02, "y": .05})
        howto_btn.bind(on_release=self._go_to_howto)
        root.add_widget(howto_btn)

        # populate buttons
        for name in self.levels:
            btn = RetroButton(text=name, size_hint_y=None, height=60)
            btn.bind(on_release=lambda btn, nm=name: self._select(nm))
            self.grid.add_widget(btn)

        with self.canvas.before:
            Color(*PALETTE["bg"]); Rectangle(size=Window.size)

        self.selected: str | None = None

    def _go_to_howto(self, *_):
        self.manager.current = "howto"

    def _select(self, name: str):
        self.selected = name; meta = self.levels[name]
        self.info.text = (
            f"[b]{name}[/b]\n"
            f"Difficulty : [color=#ff5555]{meta['difficulty']}[/color]\n"
            f"High Score : {meta['high_score']} / {meta['max_score']}\n"
            f"Stars      : {meta['stars_collected']}\n"
            f"Song       : {Path(meta['song_title']).name}"
        )
        self.start_btn.disabled = False

    def _start_level(self, *_):
        if not self.selected:   return
        meta = self.levels[self.selected]
        self.manager.get_screen("game").load_level(self.selected, meta)
        self.manager.current = "game"

# ───────────────────────── END‑OF‑LEVEL (results) SCREEN ─────────────────────────
class EndOfLevelScreen(Screen):
    """
    Shown when a level finishes.  Displays score / stars and lets the
    player replay or pick a new level.
    """
    def __init__(self, **kw):
        super().__init__(name="end", **kw)
        self.base = RelativeLayout(); self.add_widget(self.base)

        self.levels = App.get_running_app().levels

        # background
        with self.canvas.before:
            Color(*PALETTE["bg"]); Rectangle(size=Window.size)
        Window.bind(size=lambda *_: self._resize_bg())

        # headline
        self.head = RetroLabel(text="[b]LEVEL  COMPLETE[/b]",
                               font_size="48sp",
                               pos_hint={"center_x": .5, "top": 1.3})
        self.base.add_widget(self.head)

        # score / info block
        self.info = RetroLabel(text="", halign="center", valign="middle",
                               font_size="22sp",
                               size_hint=(.8, .4),
                               pos_hint={"center_x": .5, "center_y": .55})
        self.info.bind(size=lambda *_: self.info.texture_update())
        self.base.add_widget(self.info)

        # buttons
        self.replay_btn = RetroButton(text="PLAY AGAIN",
                                      size=(260, 80), size_hint=(None, None),
                                      pos_hint={"x": .15, "y": .15})
        self.replay_btn.bind(on_release=self._replay)
        self.base.add_widget(self.replay_btn)

        self.levels_btn = RetroButton(text="LEVEL  SELECT",
                                      size=(260, 80), size_hint=(None, None),
                                      pos_hint={"right": .85, "y": .15})
        self.levels_btn.bind(on_release=self._to_levels)
        self.base.add_widget(self.levels_btn)

    def _resize_bg(self):
        # resize background rect (it's the only Rectangle in canvas.before)
        self.canvas.before.children[-1].size = Window.size

    # ------------------------------------------------------------------
    #  Public API  – GameScreen calls this to populate results
    # ------------------------------------------------------------------
    def load_results(self, level_name: str, score: int):
        self.level_name = level_name
        meta = self.levels[level_name]
        stars = ScoreBoard._stars(score, meta["max_score"])
        self.info.text = (
            f"[b]{level_name}[/b]\n\n"
            f"Score : {score} / {meta['max_score']}\n"
            f"Stars : {stars}  (best  {meta['stars_collected']})\n"
            f"Difficulty : [color=#ff5555]{meta['difficulty']}[/color]\n"
            f"Song : {Path(meta['song_title']).name}"
        )
        # update persistent metadata if better
        if score > meta["high_score"]:
            meta["high_score"] = score
        if stars > meta["stars_collected"]:
            meta["stars_collected"] = stars
        save_levels(App.get_running_app().levels)

    def _replay(self, *_):
        game = self.manager.get_screen("game")
        game.load_level(self.level_name, self.levels[self.level_name])
        self.manager.current = "game"

    def _to_levels(self, *_):
        self.manager.current = "levels"


class ScoreBoard(RetroLabel):
    def __init__(self, level_name: str, display, meta, **kw):
        super().__init__(font_size="18sp", halign="left",**kw)
        self.lvl_name, self.display, self.meta = level_name, display, meta
        Clock.schedule_interval(self._refresh, .1)
        self.size_hint = (None, None)
        self.width = 500
        self.text_size = (self.width, None)  # wrap text within this width

        Window.bind(size=self._reposition)
        self._reposition()

    def _reposition(self, *_):
        self.texture_update()
        self.pos =(20, Window.height-120)

    def _refresh(self, *_):
        score = self.display.score
        max_sc = self.meta["max_score"]
        streak_text = f"Streak: {self.display.streak}"
        if self.display.streak>=3:
            streak_text += f"  [color=#ff5555]ON FIRE!!![/color]"
        self.text = (
            f"Score : {score}/{max_sc}\n"
            f"{streak_text}\n"
            f"Stars : {self._stars(score, max_sc)}"
        )
        if score > self.meta["high_score"]:
            self.meta["high_score"] = score
            app = App.get_running_app(); save_levels(app.levels)

    @staticmethod
    def _stars(score, max_sc):
        if not max_sc: return 0
        r = score/max_sc
        return 3 if r >= .9 else 2 if r >= .66 else 1 if r >= .33 else 0

class CommandOverlay(RetroLabel):
    _TXT = (
        "jump RED : [b][1][/b]\n"
        "jump GREEN : [b][2][/b]\n"
        "jump BLUE : [b][3][/b]\n\n"
        "restart : [b][r][/b]\n"
        "quit : [b][q][/b]"
    )
    def __init__(self, **kw):
        super().__init__(text=self._TXT, font_size="18sp",
                         halign="right", valign="top", **kw)
        Window.bind(size=self._reposition)
        self._reposition()

    def _reposition(self, *_):
        self.texture_update()
        self.pos = (Window.width - 210, Window.height-170)

class GameScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name="game", **kw)
        with self.canvas.before:
           Color(*PALETTE["bg"]); self._bg = Rectangle(size=Window.size)
        Window.bind(size=lambda *_: self._resize_bg())
        self.game_widget: MainWidget | None = None
        self.scoreboard : ScoreBoard | None = None
        self.cmd_overlay: CommandOverlay | None = None

        self.levels = App.get_running_app().levels

    def _resize_bg(self):
        self._bg.size = Window.size

    def load_level(self, name: str, meta: dict):
        self.clear_widgets()
        self.game_widget = MainWidget(name, meta["level_file"], meta["song_base_path"], self.manager)
        self.add_widget(self.game_widget)
        self.scoreboard = ScoreBoard(name, self.game_widget.display, meta,
                                     size_hint=(None, None),
                                     pos=(110, Window.height-120))
        self.add_widget(self.scoreboard)
        self.cmd_overlay = CommandOverlay(size_hint=(None, None),
                                     pos=(Window.width - 210, Window.height-170))
        self.add_widget(self.cmd_overlay)

    def on_key_down(self, keycode, modifiers):
        if keycode == 113: #  113 == "q"
            self.manager.current = "home"
            return
        if keycode == 114: # 114 == "r"
            self.load_level(self.game_widget.level_name, self.levels[self.game_widget.level_name])
        if self.game_widget:
            self.game_widget.on_key_down(["", keycode], modifiers)

    def on_key_up(self, keycode):
        if self.game_widget:
            self.game_widget.on_key_up(["", keycode])

class BeatBlitzApp(App):
    title = "Beat Blitz"

    def build(self):
        Window.clearcolor = PALETTE["bg"]
        self.levels = load_levels()             # shared across screens

        sm = ScreenManager(transition=FadeTransition())
        sm.add_widget(HomeScreen())
        sm.add_widget(LevelSelectScreen())
        sm.add_widget(HowToPlayScreen())
        sm.add_widget(GameScreen())
        sm.add_widget(EndOfLevelScreen())
        Window.bind(on_key_down=self._dispatch_down, on_key_up=self._dispatch_up)
        return sm

    def _dispatch_down(self, win, keycode, scancode, txt, modifiers):
        scr = self.root.current_screen
        if hasattr(scr, "on_key_down"):
            scr.on_key_down(keycode, modifiers)

    def _dispatch_up(self, win, keycode, scancode):
        scr = self.root.current_screen
        if hasattr(scr, "on_key_up"):
            scr.on_key_up(keycode)

if __name__ == "__main__":
    BeatBlitzApp().run()
