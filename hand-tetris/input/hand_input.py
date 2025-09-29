from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Tuple, List, Optional

import time
import cv2
import numpy as np
try:
    import mediapipe as mp
except ImportError:
    raise SystemExit("`pip install mediapipe` 후 다시 시도하세요.")

from logic.game import Action
from config import (
    HAND_MOVE_DEADZONE, HAND_DAS_MS, HAND_ARR_MS, HAND_RECENTER_ON_LOST,
    PINCH_CLICK_ON, PINCH_CLICK_OFF,
    PALM_BIN_COUNT,
)

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
mp_styles = mp.solutions.drawing_styles

THUMB_TIP = 4
INDEX_TIP = 8
MIDDLE_TIP = 12

@dataclass
class FingerState:
    is_down: bool = False  # 핀치 클릭 유지 상태


def l2(p1: Tuple[int,int], p2: Tuple[int,int]) -> float:
    dx = p1[0] - p2[0]
    dy = p1[1] - p2[1]
    return (dx*dx + dy*dy) ** 0.5


def to_px(lm, w: int, h: int) -> Tuple[int,int]:
    return int(lm.x * w), int(lm.y * h)


class HandController:
    def __init__(self, camera: int = 0, width: int = 1280, height: int = 720, draw: bool = False):
        self.cap = cv2.VideoCapture(camera)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.draw = draw

        # 손가락 핀치 상태
        self.state: Dict[Tuple[str,str], FingerState] = {
            ("Left","index"):  FingerState(False),
            ("Left","middle"): FingerState(False),
            ("Right","index"): FingerState(False),
            ("Right","middle"): FingerState(False),
        }

        # 손바닥 드래그(오른손) 이동 상태 (상대/연속)
        self.center_x: Optional[float] = None  # 정규화 기준 중립 x
        self.dir_held: Optional[str] = None    # 'L' / 'R' / None
        self.next_repeat_ts: int = 0
        self.last_seen_right_ts: int = 0       # 오른손 마지막 검출 시각(ms)

        self.hands = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        # 카메라 프리뷰용 마지막 프레임 (BGR)
        self.last_frame: Optional[np.ndarray] = None

    # ---------- 유틸 ----------
    @staticmethod
    def now_ms() -> int:
        return int(time.time() * 1000)

    def _update_click(self, hand: str, finger: str, dist: float) -> Optional[bool]:
        key = (hand, finger)
        st = self.state[key]
        if not st.is_down and dist <= PINCH_CLICK_ON:
            st.is_down = True
            return True
        elif st.is_down and dist >= PINCH_CLICK_OFF:
            st.is_down = False
        return None

    def _recenter_if_needed(self, right_present: bool):
        if HAND_RECENTER_ON_LOST:
            now = self.now_ms()
            if right_present:
                if self.center_x is None or (now - self.last_seen_right_ts) > 600:
                    self.center_x = None  # 다음 프레임에 재세팅
                self.last_seen_right_ts = now

    # ---------- 절대 bin 계산 ----------
    def _compute_bins(self, cx_norm: float) -> Optional[int]:
        if cx_norm < 0.4:
            return None
        rel = (cx_norm - 0.4) / 0.4  # 0..1
        bin_idx = int(rel * PALM_BIN_COUNT)
        if bin_idx >= PALM_BIN_COUNT:
            bin_idx = PALM_BIN_COUNT - 1
        return bin_idx

    # ---------- 메인 ----------
    def poll_with_meta(self) -> Tuple[List[Action], Optional[int]]:
        """액션 리스트와 절대 위치 버킷(0..PALM_BIN_COUNT-1 | None)을 함께 반환"""
        actions: List[Action] = []
        target_bin: Optional[int] = None

        ok, frame = self.cap.read()
        if not ok:
            return actions, target_bin

        frame = cv2.flip(frame, 1)
        self.last_frame = frame.copy()
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.hands.process(rgb)

        right_present = False

        if result.multi_hand_landmarks and result.multi_handedness:
            for lm, handed in zip(result.multi_hand_landmarks, result.multi_handedness):
                label = handed.classification[0].label  # "Left" / "Right"

                # 좌표 변환
                p_thumb  = to_px(lm.landmark[THUMB_TIP],  w, h)
                p_index  = to_px(lm.landmark[INDEX_TIP],  w, h)
                p_middle = to_px(lm.landmark[MIDDLE_TIP], w, h)

                d_ti = l2(p_thumb, p_index)
                d_tm = l2(p_thumb, p_middle)

                # ===== 핀치 액션 =====
                if label == "Left":
                    if self._update_click("Left", "index", d_ti):
                        actions.append(Action.ROTATE_CW)
                    # 왼손 중지는 현재 미사용
                    self._update_click("Left", "middle", d_tm)

                elif label == "Right":
                    right_present = True
                    if self._update_click("Right", "index", d_ti):
                        actions.append(Action.HARD_DROP)
                    # HOLD 제거: middle 핀치는 사용하지 않음

                    # ===== 손바닥 절대 위치 bin =====
                    p_wrist  = to_px(lm.landmark[0],  w, h)
                    p_mcp_m  = to_px(lm.landmark[9],  w, h)
                    cx = (p_wrist[0] + p_mcp_m[0]) / 2.0
                    cx_norm = cx / float(w)
                    target_bin = self._compute_bins(cx_norm)

                    # ===== (선택) 상대/연속 이동 유지 =====
                    if not self.state[("Right","index")].is_down:
                        if self.center_x is None:
                            self.center_x = cx_norm
                            self.dir_held = None
                            self.next_repeat_ts = 0
                        else:
                            dx = cx_norm - self.center_x
                            now = self.now_ms()
                            if dx > HAND_MOVE_DEADZONE:
                                if self.dir_held != "R":
                                    actions.append(Action.MOVE_RIGHT)
                                    self.dir_held = "R"
                                    self.next_repeat_ts = now + HAND_DAS_MS
                                elif now >= self.next_repeat_ts:
                                    actions.append(Action.MOVE_RIGHT)
                                    self.next_repeat_ts = now + HAND_ARR_MS
                            elif dx < -HAND_MOVE_DEADZONE:
                                if self.dir_held != "L":
                                    actions.append(Action.MOVE_LEFT)
                                    self.dir_held = "L"
                                    self.next_repeat_ts = now + HAND_DAS_MS
                                elif now >= self.next_repeat_ts:
                                    actions.append(Action.MOVE_LEFT)
                                    self.next_repeat_ts = now + HAND_ARR_MS
                            else:
                                self.dir_held = None
                                self.next_repeat_ts = 0

                # 디버그
                if self.draw:
                    mp_draw.draw_landmarks(
                        frame, lm, mp_hands.HAND_CONNECTIONS,
                        mp_styles.get_default_hand_landmarks_style(),
                        mp_styles.get_default_hand_connections_style(),
                    )
                    cv2.line(frame, p_thumb, p_index,  (60,200,255), 2)
                    cv2.line(frame, p_thumb, p_middle, (255,180,80), 2)
                    cv2.putText(frame, f"TI {d_ti:.0f}px TM {d_tm:.0f}px", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 1, cv2.LINE_AA)

        # 중립 재설정
        self._recenter_if_needed(right_present)

        if self.draw and self.last_frame is not None:
            cv2.imshow("Hand Input", self.last_frame)
            cv2.waitKey(1)

        return actions, target_bin

    
    def poll(self) -> List[Action]:
        actions, _ = self.poll_with_meta()
        return actions

    def get_last_frame(self) -> Optional[np.ndarray]:
        return self.last_frame

    def release(self):
        self.hands.close()
        self.cap.release()
        cv2.destroyAllWindows()
