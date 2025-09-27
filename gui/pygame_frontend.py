import pygame
from typing import Tuple, Optional

from logic.game import Game, Action, GameState, SHAPES
from config import BOARD_COLS, BOARD_ROWS, CELL_SIZE, MARGIN, FPS, COLORS, NEXT_PREVIEW_COUNT, PALM_BIN_COUNT


from input.hand_input import HandController

import cv2

FONT_NAME = "arial"

HAND_AVAILABLE = True

def run(use_hand: bool = True, hand_draw_preview: bool = False, use_absolute_bins: bool = True):
    pygame.init()
    pygame.display.set_caption("Hand-Tetris")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(FONT_NAME, 20)
    big = pygame.font.SysFont(FONT_NAME, 24, bold=True)

    # Layout: playfield + right panel (NEXT + score) + camera below
    play_w = BOARD_COLS * CELL_SIZE
    play_h = BOARD_ROWS * CELL_SIZE
    side_w = 9 * CELL_SIZE

    screen = pygame.display.set_mode((play_w + side_w + 3*MARGIN, play_h + 2*MARGIN))

    game = Game(rows=BOARD_ROWS, cols=BOARD_COLS)

    hand = None
    if use_hand and HAND_AVAILABLE:
        hand = HandController(camera=0, draw=hand_draw_preview)
    elif use_hand and not HAND_AVAILABLE:
        print("HandController 사용 불가.")

    running = True
    try:
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_LEFT:
                        game.step(Action.MOVE_LEFT)
                    elif event.key == pygame.K_RIGHT:
                        game.step(Action.MOVE_RIGHT)
                    elif event.key == pygame.K_UP:
                        game.step(Action.ROTATE_CW)
                    elif event.key == pygame.K_z:
                        game.step(Action.ROTATE_CCW)
                    elif event.key == pygame.K_DOWN:
                        game.step(Action.SOFT_DROP)
                    elif event.key == pygame.K_SPACE:
                        game.step(Action.HARD_DROP)

            target_bin: Optional[int] = None
            if hand is not None:
                if use_absolute_bins and hasattr(hand, 'poll_with_meta'):
                    acts, target_bin = hand.poll_with_meta()
                    for act in acts:
                        game.step(act)
                else:
                    for act in hand.poll():
                        game.step(act)

            if use_hand and use_absolute_bins and target_bin is not None and game.state is GameState.RUNNING and game.active is not None:
                desired_c = _target_col_from_bin(game, target_bin)
                if game.active.c < desired_c:
                    game.step(Action.MOVE_RIGHT)
                elif game.active.c > desired_c:
                    game.step(Action.MOVE_LEFT)

            game.step(Action.TICK)

            # --- Render ---
            screen.fill(COLORS["bg"])

            field_rect = pygame.Rect(MARGIN, MARGIN, play_w, play_h)
            pygame.draw.rect(screen, COLORS["frame"], field_rect, width=2)

            for r in range(BOARD_ROWS):
                y = MARGIN + r*CELL_SIZE
                pygame.draw.line(screen, COLORS["grid"], (MARGIN, y), (MARGIN+play_w, y))
            for c in range(BOARD_COLS):
                x = MARGIN + c*CELL_SIZE
                pygame.draw.line(screen, COLORS["grid"], (x, MARGIN), (x, MARGIN+play_h))

            for r, c in game.get_ghost_cells():
                draw_cell(screen, r, c, (255,255,255), alpha=70)

            for r, c, k in game.get_cells():
                draw_cell(screen, r, c, COLORS[k])

            panel_x = MARGIN*2 + play_w
            panel_y = MARGIN

            # NEXT panel
            title = big.render("NEXT", True, COLORS["text"])
            screen.blit(title, (panel_x, panel_y))
            panel_y += 28

            queue = game.get_next_queue()[:NEXT_PREVIEW_COUNT]
            for i, kind in enumerate(queue):
                draw_mini_piece(screen, kind, panel_x, panel_y + i*CELL_SIZE*3)

            info_y = panel_y + NEXT_PREVIEW_COUNT*CELL_SIZE*3 + 10
            score_surf = font.render(f"Score: {game.score}", True, COLORS["text"])
            lines_surf = font.render(f"Lines: {game.lines_cleared}", True, COLORS["text"])
            screen.blit(score_surf, (panel_x, info_y))
            screen.blit(lines_surf, (panel_x, info_y + 22))

            # Camera preview (below the info)
            cam_frame = hand.get_last_frame() if hand is not None else None
            if cam_frame is not None:
                cam_h = int(CELL_SIZE * 6)
                cam_w = CELL_SIZE * 8
                preview = cv2.cvtColor(cam_frame, cv2.COLOR_BGR2RGB)
                preview = cv2.resize(preview, (cam_w, cam_h))
                surf = pygame.image.frombuffer(preview.tobytes(), (cam_w, cam_h), 'RGB')
                screen.blit(surf, (panel_x, info_y + 48))

            # hint = font.render("←/→ Move  ↑/Z Rot  ↓ Soft  SPACE Hard  |  Palm bins ON | Hold removed", True, COLORS["text"])
            # screen.blit(hint, (MARGIN + 8, play_h + MARGIN - 24))

            if game.state is GameState.GAME_OVER:
                overlay = big.render("GAME OVER — press ESC", True, COLORS["text"])
                screen.blit(overlay, (MARGIN + 12, MARGIN + 12))

            pygame.display.flip()
            clock.tick(FPS)
    finally:
        if hand is not None:
            hand.release()
        pygame.quit()


def draw_cell(screen, r: int, c: int, color: Tuple[int,int,int], alpha: int = 255):
    x = MARGIN + c*CELL_SIZE
    y = MARGIN + r*CELL_SIZE
    rect = pygame.Rect(x+1, y+1, CELL_SIZE-2, CELL_SIZE-2)
    if alpha >= 255:
        pygame.draw.rect(screen, color, rect, border_radius=6)
    else:
        surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        surface.fill((*color, alpha))
        screen.blit(surface, rect)


def draw_mini_piece(screen, kind: str, x: int, y: int):
    grid = SHAPES[kind][0]
    color = COLORS[kind]
    for rr in range(4):
        for cc in range(4):
            if grid[rr][cc]:
                cx = x + cc* (CELL_SIZE//2) + CELL_SIZE
                cy = y + rr* (CELL_SIZE//2) + CELL_SIZE//2
                rect = pygame.Rect(cx, cy, CELL_SIZE//2 - 2, CELL_SIZE//2 - 2)
                pygame.draw.rect(screen, color, rect, border_radius=4)


def _target_col_from_bin(game: Game, bin_idx: int) -> int:
    assert game.active is not None
    kind = game.active.kind
    rot = game.active.rot % 4
    grid = SHAPES[kind][rot]

    min_cc, max_cc = 3, 0
    for rr in range(4):
        for cc in range(4):
            if grid[rr][cc]:
                if cc < min_cc: min_cc = cc
                if cc > max_cc: max_cc = cc
    piece_width = max_cc - min_cc + 1

    board_col = int(round((bin_idx / max(1, PALM_BIN_COUNT-1)) * (game.cols - 1)))
    c_target = board_col - min_cc
    c_min = 0
    c_max = game.cols - piece_width
    if c_target < c_min: c_target = c_min
    if c_target > c_max: c_target = c_max

    return c_target


if __name__ == "__main__":
    run(use_hand=True, hand_draw_preview=False, use_absolute_bins=True)
