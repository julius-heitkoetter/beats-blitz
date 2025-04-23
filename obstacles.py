from kivy.graphics.instructions import InstructionGroup
from kivy.graphics import Color, Line, Rectangle

from constants import SLICE_WIDTH

class CollisionResult:
    """
    Simple struct to communicate collision type:
      - top:    player is on top of the obstacle
      - bottom: player hits the obstacle from below (like a ceiling)
      - side:   player hits side => death
      - none:   no collision
      - spike:  immediate death (for spikes)
    """
    def __init__(self, ctype='none', topY=None):
        self.ctype = ctype
        self.topY  = topY  # if landed on top, store the y-level of that top.

class Obstacle(InstructionGroup):
    """
    Base obstacle class. Subclasses override _init_graphics() and
    collision test to differentiate top/bottom/side/spike collisions.
    """
    def __init__(self, slice_idx, data):
        super(Obstacle, self).__init__()
        self.slice_idx = slice_idx
        self.data      = data  # dictionary from JSON
        self.x         = 0
        self.y         = 0
        self.width     = SLICE_WIDTH
        self.height    = 0
        self._init_graphics()

    def _init_graphics(self):
        pass

    def set_position(self, x, y):
        self.x = x
        self.y = y

    def on_update(self, dt):
        pass

    def check_collision(self, px, py, psize, vy):
        """
        Return a CollisionResult describing how the player collides with
        this obstacle, if at all.

        px, py   = player's left, bottom
        psize    = size of the player's square
        vy       = player's vertical velocity
        """
        return CollisionResult('none')


class Empty(Obstacle):
    def _init_graphics(self):
        self.height = 0  # effectively no vertical shape

    def check_collision(self, px, py, psize, vy):
        # always no collision with empty
        return CollisionResult('none')

class Spikes(Obstacle):
    """
    For spikes, *any* overlap is an immediate 'spike' collision => death.
    We'll approximate it with a bounding box from (x, y) up to (x+width, y+spike_height).
    """
    def _init_graphics(self):
        self.spike_height = 50
        self.height       = self.spike_height
        self.color        = Color(1,1,1)
        self.line         = Line(points=[], width=1)
        self.add(self.color)
        self.add(self.line)

    def set_position(self, x, y):
        super().set_position(x,y)
        x1 = x
        y1 = y
        x2 = x + self.width/2
        y2 = y + self.spike_height
        x3 = x + self.width
        y3 = y
        self.line.points = [x1,y1, x2,y2, x3,y3, x1,y1]

    def check_collision(self, px, py, psize, vy):
        # bounding box for spikes
        spike_top = self.y + self.spike_height
        spike_left = self.x
        spike_right= self.x + self.width

        # if the player's bounding box overlaps the spike's bounding box => 'spike' => immediate death
        if (px+psize > spike_left and px < spike_right and
            py+psize > self.y and py < spike_top):
            return CollisionResult('spike')
        return CollisionResult('none')


class Tower(Obstacle):
    """
    A vertical tower of blocks with a top. If the player hits the side => side collision => death.
    If the player's bottom meets the top => top collision => can stand.
    If the player's top meets the bottom => bottom collision => bump head.
    """
    def _init_graphics(self):
        n = self.data.get('height', 1)
        block_height = 40
        self.height  = n * block_height
        self.color   = Color(1,1,1)
        self.rect    = Rectangle()
        self.add(self.color)
        self.add(self.rect)

    def set_position(self, x, y):
        super().set_position(x, y)
        self.rect.pos  = (x, y)
        self.rect.size = (self.width, self.height)

    def check_collision(self, px, py, psize, vy):
        # bounding box of tower is (x, y) -> (x+width, y+height)
        left   = self.x
        right  = self.x + self.width
        bottom = self.y
        top    = self.y + self.height

        player_left   = px
        player_right  = px + psize
        player_bottom = py
        player_top    = py + psize

        # check bounding-box overlap
        if (player_right > left and player_left < right and
            player_top > bottom and player_bottom < top):

            # We have some overlap, so figure out if it's top/bottom/side.
            # We'll check the player's previous vertical direction via `vy`.
            #  1) If player's bottom is near the top => top collision => land
            #  2) If player's top is near the bottom => bottom collision => bump
            #  3) otherwise => side collision => death

            # small epsilon for "landing" threshold
            epsilon = 5

            # The player's bottom is just at or slightly below the tower's top.
            # And the player is moving downward (vy <= 0):
            if abs(player_bottom - top) < epsilon and vy <= 0:
                return CollisionResult('top', topY=top)

            # The player's top is near the tower's bottom, and the player is moving upward (vy >= 0)
            if abs(player_top - bottom) < epsilon and vy >= 0:
                return CollisionResult('bottom', topY=bottom)

            # Otherwise side collision => death
            return CollisionResult('side')

        return CollisionResult('none')


class TowerWithSpikes(Tower):
    """
    A tower plus an extra spike on top. If the player touches the spike area => spike => death.
    Otherwise same as tower.
    """
    def _init_graphics(self):
        super()._init_graphics()
        self.spike_height = 30
        self.spike_color  = Color(1,1,1)
        self.spike_line   = Line(points=[], width=1)
        self.add(self.spike_color)
        self.add(self.spike_line)

    def set_position(self, x, y):
        super().set_position(x, y)
        # The spike is drawn on top:
        spike_x1 = x
        spike_y1 = y + self.height
        spike_x2 = x + self.width/2
        spike_y2 = y + self.height + self.spike_height
        spike_x3 = x + self.width
        spike_y3 = y + self.height
        self.spike_line.points = [spike_x1, spike_y1,
                                  spike_x2, spike_y2,
                                  spike_x3, spike_y3,
                                  spike_x1, spike_y1]

    def check_collision(self, px, py, psize, vy):
        # first check if we collide with the spike region
        spike_region_top = self.y + self.height + self.spike_height
        spike_region_bottom = self.y + self.height
        spike_left = self.x
        spike_right= self.x + self.width

        player_left   = px
        player_right  = px + psize
        player_bottom = py
        player_top    = py + psize

        # if bounding box overlaps the spike region => 'spike'
        if (player_right > spike_left and player_left < spike_right and
            player_top > spike_region_bottom and player_bottom < spike_region_top):
            return CollisionResult('spike')

        # else, handle normal tower bounding box
        result = super().check_collision(px, py, psize, vy)
        if result.ctype == 'top':
            # Actually, the "top" of the tower is slightly lower than the spikes
            # So we do NOT let the player land on the spiked top.
            # We'll treat that as a side collision => death if they try to step
            # on top. But you can keep it if you want the player to stand below spikes.
            # Let's say we reduce the top by spike_height in the bounding box:
            tower_only_top = self.y + (self.height - self.spike_height)
            # if the collision said top = y + height, check if that's valid:
            if result.topY >= tower_only_top:
                # That means the top is effectively where the spikes begin => no landing
                return CollisionResult('side')
        return result

class FloatingSquare(Obstacle):
    """
    A single square floating above the ground. If you land on top => top collision.
    If you hit it from below => bottom collision. If from side => side collision.
    """
    def _init_graphics(self):
        n = self.data.get('height', 1)
        self.block_size = 40
        self.floating_offset = n * 50
        self.height = self.block_size
        self.color  = Color(1,1,1)
        self.rect   = Rectangle()
        self.add(self.color)
        self.add(self.rect)

    def set_position(self, x, y):
        # y => ground-level, but we want to float above
        super().set_position(x, y + self.floating_offset)
        self.rect.pos  = (self.x, self.y)
        self.rect.size = (self.width, self.block_size)

    def check_collision(self, px, py, psize, vy):
        left   = self.x
        right  = self.x + self.width
        bottom = self.y
        top    = self.y + self.block_size

        player_left   = px
        player_right  = px + psize
        player_bottom = py
        player_top    = py + psize

        if (player_right > left and player_left < right and
            player_top > bottom and player_bottom < top):
            epsilon = 5
            # top collision
            if abs(player_bottom - top) < epsilon and vy <= 0:
                return CollisionResult('top', topY=top)
            # bottom collision
            if abs(player_top - bottom) < epsilon and vy >= 0:
                return CollisionResult('bottom', topY=bottom)
            # side
            return CollisionResult('side')

        return CollisionResult('none')


class FloatingSquareWithSpikes(FloatingSquare):
    """
    Like FloatingSquare but with spikes on top or bottom.
    If the spikes are on top => 'spike' region above the square.
    If the spikes are on bottom => 'spike' region below the square.
    """
    def _init_graphics(self):
        super()._init_graphics()
        self.spike_height = 20
        self.spikes_on_top = self.data.get('spikesOnTop', True)
        self.spike_color = Color(1,1,1)
        self.spike_line  = Line(points=[], width=1)
        self.add(self.spike_color)
        self.add(self.spike_line)

    def set_position(self, x, y):
        super().set_position(x, y)
        if self.spikes_on_top:
            sx1 = self.x
            sy1 = self.y + self.block_size
            sx2 = self.x + self.width/2
            sy2 = self.y + self.block_size + self.spike_height
            sx3 = self.x + self.width
            sy3 = self.y + self.block_size
            self.spike_line.points = [sx1,sy1, sx2,sy2, sx3,sy3, sx1,sy1]
        else:
            sx1 = self.x
            sy1 = self.y
            sx2 = self.x + self.width/2
            sy2 = self.y - self.spike_height
            sx3 = self.x + self.width
            sy3 = self.y
            self.spike_line.points = [sx1,sy1, sx2,sy2, sx3,sy3, sx1,sy1]

    def check_collision(self, px, py, psize, vy):
        # check the spike region first
        left  = self.x
        right = self.x + self.width

        if self.spikes_on_top:
            spike_bottom = self.y + self.block_size
            spike_top    = spike_bottom + self.spike_height
        else:
            spike_top    = self.y
            spike_bottom = self.y - self.spike_height

        player_left   = px
        player_right  = px + psize
        player_bottom = py
        player_top    = py + psize

        # spike bounding box overlap => immediate death
        if (player_right > left and player_left < right and
            player_top > spike_bottom and player_bottom < spike_top):
            return CollisionResult('spike')

        # otherwise, behave like normal floating square
        return super(FloatingSquare, self).check_collision(px, py, psize, vy)

# ---------------------------------------------------------
#  FACTORY FOR OBSTACLES
# ---------------------------------------------------------
def obstacle_factory(slice_idx, data):
    otype = data.get('type', 'empty')
    if otype == 'empty':
        return Empty(slice_idx, data)
    elif otype == 'spikes':
        return Spikes(slice_idx, data)
    elif otype == 'tower':
        return Tower(slice_idx, data)
    elif otype == 'towerWithSpikes':
        return TowerWithSpikes(slice_idx, data)
    elif otype == 'floatingSquare':
        return FloatingSquare(slice_idx, data)
    elif otype == 'floatingSquareWithSpikes':
        return FloatingSquareWithSpikes(slice_idx, data)
    else:
        return Empty(slice_idx, data)
