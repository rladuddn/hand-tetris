# ===== logic/game.py (no HOLD) =====
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
import random
from typing import List, Tuple, Optional

# ===== Shapes (rotation states as 4x4 grids) =====
SHAPES = {
    "I": [
        [(0,1,0,0), (0,1,0,0), (0,1,0,0), (0,1,0,0)],
        [(0,0,0,0), (1,1,1,1), (0,0,0,0), (0,0,0,0)],
        [(0,0,1,0), (0,0,1,0), (0,0,1,0), (0,0,1,0)],
        [(0,0,0,0), (0,0,0,0), (1,1,1,1), (0,0,0,0)],
    ],
    "O": [
        [(0,0,0,0), (0,1,1,0), (0,1,1,0), (0,0,0,0)],
    ] * 4,
    "T": [
        [(0,0,0,0), (1,1,1,0), (0,1,0,0), (0,0,0,0)],
        [(0,1,0,0), (1,1,0,0), (0,1,0,0), (0,0,0,0)],
        [(0,1,0,0), (1,1,1,0), (0,0,0,0), (0,0,0,0)],
        [(0,1,0,0), (0,1,1,0), (0,1,0,0), (0,0,0,0)],
    ],
    "S": [
        [(0,0,0,0), (0,1,1,0), (1,1,0,0), (0,0,0,0)],
        [(1,0,0,0), (1,1,0,0), (0,1,0,0), (0,0,0,0)],
        [(0,0,0,0), (0,1,1,0), (1,1,0,0), (0,0,0,0)],
        [(1,0,0,0), (1,1,0,0), (0,1,0,0), (0,0,0,0)],
    ],
    "Z": [
        [(0,0,0,0), (1,1,0,0), (0,1,1,0), (0,0,0,0)],
        [(0,1,0,0), (1,1,0,0), (1,0,0,0), (0,0,0,0)],
        [(0,0,0,0), (1,1,0,0), (0,1,1,0), (0,0,0,0)],
        [(0,1,0,0), (1,1,0,0), (1,0,0,0), (0,0,0,0)],
    ],
    "J": [
        [(0,0,0,0), (1,1,1,0), (0,0,1,0), (0,0,0,0)],
        [(0,1,0,0), (0,1,0,0), (1,1,0,0), (0,0,0,0)],
        [(1,0,0,0), (1,1,1,0), (0,0,0,0), (0,0,0,0)],
        [(0,1,1,0), (0,1,0,0), (0,1,0,0), (0,0,0,0)],
    ],
    "L": [
        [(0,0,0,0), (1,1,1,0), (1,0,0,0), (0,0,0,0)],
        [(1,1,0,0), (0,1,0,0), (0,1,0,0), (0,0,0,0)],
        [(0,0,1,0), (1,1,1,0), (0,0,0,0), (0,0,0,0)],
        [(0,1,0,0), (0,1,0,0), (0,1,1,0), (0,0,0,0)],
    ],
}

KICK_TABLE = [(0,0), (0,1), (0,-1), (1,0), (-1,0)]  # simple kicks

class Action(Enum):
    MOVE_LEFT = auto()
    MOVE_RIGHT = auto()
    SOFT_DROP = auto()
    HARD_DROP = auto()
    ROTATE_CW = auto()
    ROTATE_CCW = auto()
    TICK = auto()

class GameState(Enum):
    RUNNING = auto()
    GAME_OVER = auto()

@dataclass
class Piece:
    kind: str
    r: int
    c: int
    rot: int = 0

    @property
    def cells(self) -> List[Tuple[int,int]]:
        grid = SHAPES[self.kind][self.rot % 4]
        out = []
        for rr in range(4):
            for cc in range(4):
                if grid[rr][cc]:
                    out.append((self.r + rr, self.c + cc))
        return out

@dataclass
class Game:
    rows: int = 20
    cols: int = 10
    gravity_frames: int = 48
    soft_drop_frames: int = 2
    lock_delay_frames: int = 30

    grid: List[List[Optional[str]]] = field(default_factory=list)
    rng: random.Random = field(default_factory=random.Random)
    state: GameState = GameState.RUNNING

    active: Optional[Piece] = None
    next_queue: List[str] = field(default_factory=list)
    bag: List[str] = field(default_factory=list)

    score: int = 0
    lines_cleared: int = 0
    frame_counter: int = 0
    lock_counter: int = 0

    def __post_init__(self):
        if not self.grid:
            self.grid = [[None for _ in range(self.cols)] for _ in range(self.rows)]
        self._refill_bag()
        for _ in range(4):
            self._push_next(self._draw_bag())
        self._spawn_next()

    # ----- Random bag -----
    def _refill_bag(self):
        self.bag = ["I","O","T","S","Z","J","L"]
        self.rng.shuffle(self.bag)

    def _draw_bag(self) -> str:
        if not self.bag:
            self._refill_bag()
        return self.bag.pop()

    def _push_next(self, k: str):
        self.next_queue.append(k)

    def _pop_next(self) -> str:
        if len(self.next_queue) < 4:
            self._push_next(self._draw_bag())
        return self.next_queue.pop(0)

    # ----- Spawning -----
    def _spawn(self, kind: str):
        self.active = Piece(kind=kind, r=0, c=3, rot=0)
        while len(self.next_queue) < 4:
            self._push_next(self._draw_bag())
        if self._collides(self.active):
            self.state = GameState.GAME_OVER

    def _spawn_next(self):
        kind = self._pop_next()
        self._spawn(kind)

    # ----- Collision -----
    def _collides(self, p: Piece) -> bool:
        for r, c in p.cells:
            if r < 0 or r >= self.rows or c < 0 or c >= self.cols:
                return True
            if self.grid[r][c] is not None:
                return True
        return False

    # ----- Lock piece -----
    def _lock_active(self):
        assert self.active is not None
        for r, c in self.active.cells:
            if 0 <= r < self.rows and 0 <= c < self.cols:
                self.grid[r][c] = self.active.kind
        cleared = self._clear_lines()
        self._update_score(cleared)
        self._spawn_next()
        self.lock_counter = 0

    def _clear_lines(self) -> int:
        new_grid = [row for row in self.grid if any(cell is None for cell in row)]
        cleared = self.rows - len(new_grid)
        for _ in range(cleared):
            new_grid.insert(0, [None]*self.cols)
        self.grid = new_grid
        self.lines_cleared += cleared
        return cleared

    def _update_score(self, cleared: int):
        table = {0: 0, 1: 100, 2: 300, 3: 500, 4: 800}
        self.score += table.get(cleared, 0)

    # ----- Public: step -----
    def step(self, action: Action):
        if self.state is not GameState.RUNNING:
            return
        if action == Action.TICK:
            self._tick(); return
        if self.active is None:
            return

        if action == Action.MOVE_LEFT:
            self._try_move(dcol=-1)
        elif action == Action.MOVE_RIGHT:
            self._try_move(dcol=1)
        elif action == Action.SOFT_DROP:
            self._try_move(drow=1)
        elif action == Action.HARD_DROP:
            while self._try_move(drow=1):
                pass
            self._lock_active()
        elif action == Action.ROTATE_CW:
            self._try_rotate(+1)
        elif action == Action.ROTATE_CCW:
            self._try_rotate(-1)

    def _tick(self):
        self.frame_counter += 1
        if self.active is None:
            return
        grav = self.gravity_frames
        if self.frame_counter % grav == 0:
            moved = self._try_move(drow=1)
            if not moved:
                self.lock_counter += 1
                if self.lock_counter >= self.lock_delay_frames:
                    self._lock_active()
            else:
                self.lock_counter = 0

    def _try_move(self, drow: int = 0, dcol: int = 0) -> bool:
        assert self.active is not None
        p = Piece(self.active.kind, self.active.r + drow, self.active.c + dcol, self.active.rot)
        if not self._collides(p):
            self.active = p
            return True
        return False

    def _try_rotate(self, dr: int) -> bool:
        assert self.active is not None
        orig = self.active
        for kr, kc in KICK_TABLE:
            candidate = Piece(orig.kind, orig.r + kr, orig.c + kc, (orig.rot + dr) % 4)
            if not self._collides(candidate):
                self.active = candidate
                return True
        return False

    # ----- Queries for rendering -----
    def get_cells(self) -> List[Tuple[int,int,str]]:
        out = []
        for r in range(self.rows):
            for c in range(self.cols):
                k = self.grid[r][c]
                if k:
                    out.append((r,c,k))
        if self.active is not None:
            for r, c in self.active.cells:
                out.append((r,c,self.active.kind))
        return out

    def get_ghost_cells(self) -> List[Tuple[int,int]]:
        if self.active is None:
            return []
        ghost = Piece(self.active.kind, self.active.r, self.active.c, self.active.rot)
        while not self._collides(Piece(ghost.kind, ghost.r+1, ghost.c, ghost.rot)):
            ghost.r += 1
        return ghost.cells

    def get_next_queue(self) -> List[str]:
        return list(self.next_queue[:])

