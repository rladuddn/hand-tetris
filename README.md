# Hand‑Gesture Tetris (Python + Pygame + MediaPipe)

~readme는 귀찮아서 gpt에게 작성을 맡겼습니다~

카메라의 **손 제스처**로 플레이하는 테트리스 입니다.

* 10×20 보드, 다음 피스 **4개** 미리보기, 고스트 표시
* **왼손 검지 핀치 → 회전**, **오른손 검지 핀치 → 하드드롭**
* **손바닥 X 위치(화면 중앙~오른쪽)**를 **10등분(bin)** → 해당 칼럼으로 **절대 스냅 이동**
* 게임 화면 **우측 패널에 카메라 프리뷰** 표시
* 키보드 입력 병행 지원
* ※ 요구에 따라 **HOLD(홀드) 기능은 제거**됨

---

## 사전설정

* Python **3.9 ~ 3.11** 권장
* 패키지: `pygame`, `opencv-python`, `mediapipe`

```bash
pip install --upgrade pip
pip install pygame opencv-python mediapipe
```

> **macOS/리눅스**: IDE/터미널의 **카메라 권한**을 허용하세요. 다른 앱이 카메라를 점유 중이면 `VideoCapture(0)`가 실패합니다.

---

## 📦 프로젝트 구조

**패키지 구조**(선택):

```
project_root/
├─ main.py
├─ gui/pygame_frontend.py
├─ logic/game.py
├─ input/hand_input.py
├─ config.py
└─ (각 폴더에 __init__.py 권장)
```

> 패키지 구조를 사용할 때는 **항상 루트에서** `python main.py`로 실행하세요.

---

## 실행

```bash
python main.py
```

* 기본값: 손 제스처 ON, 카메라 프리뷰 ON, **palm bins 기반 절대 위치 이동** ON

### 키보드 조작

* `←/→` 이동, `↑` 또는 `Z` 회전, `↓` 소프트드롭, `Space` 하드드롭, `Esc` 종료

---

## 제스처 매핑

* **왼손 검지 핀치**(엄지–검지 거리 ≤ `PINCH_CLICK_ON`) → **회전(시계)**
* **오른손 검지 핀치** → **하드드롭**
* **오른손 손바닥 X** → 화면 **중앙(0.5)~오른쪽(1.0)** 구간을 `PALM_BIN_COUNT=10`으로 등분하여 **해당 칼럼으로 스냅**

  * 중앙보다 왼쪽( `< 0.5` )이면 스냅 없음(유지)

> 필요시 **상대/연속 이동**(DAS/ARR) 로직도 `hand_input.py`에 남아 있어 활성화할 수 있습니다.

---

## 설정 (config.py)

* `BOARD_COLS=10`, `BOARD_ROWS=20`, `CELL_SIZE=32`, `FPS=60`
* 중력/속도: `INITIAL_GRAVITY_FRAMES=48`, `SOFT_DROP_GRAVITY_FRAMES=2`, `LOCK_DELAY_FRAMES=30`
* 프리뷰 개수: `NEXT_PREVIEW_COUNT=4`
* **손 입력 파라미터**

  * `PINCH_CLICK_ON=30.0`, `PINCH_CLICK_OFF=40.0` (픽셀, 히스테리시스)
  * `PALM_BIN_COUNT=10` (중앙~오른쪽 등분 개수)
  * (선택) 연속 이동 튜닝: `HAND_MOVE_DEADZONE`, `HAND_DAS_MS`, `HAND_ARR_MS`, `HAND_RECENTER_ON_LOST`

---

## 동작 개요

1. `hand_input.py`가 **MediaPipe Hands**로 양손 랜드마크를 추정.
2. 엄지–검지/중지 거리로 **핀치 클릭**을 감지.
3. 오른손 손목·중지 MCP의 평균 X를 화면 폭으로 정규화 → **중앙~오른쪽을 10등분**하여 `target_bin` 산출.
4. `pygame_frontend.py`가 `target_bin → 보드 칼럼`으로 매핑하고, **프레임마다 1칸씩 안전 이동**하여 스냅.
5. 카메라 프리뷰는 `hand_input.get_last_frame()`을 통해 GUI에 표시.

---

## 🩺 트러블슈팅

### `[INFO] HandController 사용 불가(미설치 또는 에러)`가 뜰 때

1. **패키지 설치 확인**

```bash
python -c "import cv2, mediapipe as mp; print('cv2', cv2.__version__, '| mp', mp.__version__)"
```

2. **임포트 경로**

* 단일 파일 구조면 `pygame_frontend.py`에서

  ```python
  from game import Game, Action, GameState, SHAPES
  from hand_input import HandController
  ```

  처럼 **단일 파일 임포트**를 사용하세요.
* 패키지 구조면 각 폴더에 `__init__.py`가 있고, 루트에서 `python main.py`로 실행해야 합니다.

3. **카메라 장치/권한**

```bash
python - << 'PY'
import cv2
cap = cv2.VideoCapture(0)
print('opened:', cap.isOpened())
ret, frame = cap.read()
print('read:', ret)
cap.release()
PY
```

* `opened: False`면 다른 앱 점유/권한/인덱스 문제일 수 있습니다. `camera=1`로 바꿔보세요.

> 디버깅을 돕기 위해 `pygame_frontend.py`의 HandController 임포트 부분에 `traceback.print_exc()`를 추가하면 **정확한 원인**을 즉시 확인할 수 있습니다.

---

## 팁/튜닝

* 스냅을 더 빠르게 하고 싶다면, `pygame_frontend.py`에서 **프레임당 여러 칸** 이동(예: 최대 3칸)하도록 변경할 수 있습니다.
* 핀치 감도가 너무 빡빡/느슨하면 `PINCH_CLICK_ON/OFF`를 ±5~10px 범위에서 조절.
* `PALM_BIN_COUNT`를 12~16으로 늘리면 더 세밀한 칼럼 지정이 가능합니다.

---

## 라이선스

학습/데모 목적으로 자유롭게 수정/사용 가능합니다.
