# Global configuration for the Tetris demo

BOARD_COLS = 10
BOARD_ROWS = 20
CELL_SIZE = 32  # px
MARGIN = 4      # px between playfield and panels
FPS = 60

# Gravity and speed tuning (frames at 60 fps)
INITIAL_GRAVITY_FRAMES = 48  # lower = faster
SOFT_DROP_GRAVITY_FRAMES = 2
LOCK_DELAY_FRAMES = 30

NEXT_PREVIEW_COUNT = 4



# 좌/우 이동: 손바닥 드래그(오른손 기준)
HAND_MOVE_DEADZONE = 0.05     
HAND_DAS_MS = 160             # Initial Delay Auto Shift
HAND_ARR_MS = 55              # Auto Repeat Rate
HAND_RECENTER_ON_LOST = True  # 중립 재설정

# 클릭 인식(핀치): 엄지–검지 / 엄지–중지 거리 기준 (픽셀)
PINCH_CLICK_ON = 40.0         # 클릭 진입 임계 (<=)
PINCH_CLICK_OFF = 60.0        # 클릭 해제 임계 (>=)


PALM_BIN_COUNT = 10           
PALM_BIN_SIDE = "right"       

# Colors (R, G, B)
COLORS = {
    "bg": (18, 18, 22),
    "grid": (40, 40, 48),
    "frame": (80, 80, 95),
    "text": (230, 230, 240),
    # Tetromino colors
    "I": (0, 186, 255),
    "O": (255, 209, 0),
    "T": (191, 81, 255),
    "S": (0, 204, 136),
    "Z": (255, 65, 65),
    "J": (0, 112, 224),
    "L": (255, 144, 0),
}
