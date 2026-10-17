import ctypes
import math
import os
import queue
import sys
import threading
import time
import urllib.request
import cv2

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from core.audio_fx import (
    play_click,
    play_explode,
    play_lock,
    play_snap,
    play_vol_tick,
    play_whoosh,
)
from core.speech import is_speaking, stop_speaking

# Win32 Hardware Input Emulation
user32 = ctypes.windll.user32
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
VK_LWIN = 0x5B
VK_D = 0x44
VK_VOLUME_UP = 0xAF
VK_VOLUME_DOWN = 0xAE
KEYEVENTF_KEYUP = 0x0002

MODEL_PATH = os.path.join(os.path.dirname(__file__), "hand_landmarker.task")
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"

telemetry_queue = queue.Queue(maxsize=2)


def ensure_model_exists():
    if not os.path.exists(MODEL_PATH):
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)


def win32_hotkey_win_d():
    user32.keybd_event(VK_LWIN, 0, 0, 0)
    user32.keybd_event(VK_D, 0, 0, 0)
    user32.keybd_event(VK_D, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)


def win32_volume_adjust(up=True):
    vk = VK_VOLUME_UP if up else VK_VOLUME_DOWN
    user32.keybd_event(vk, 0, 0, 0)
    user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)


class HeadlessSpatialTracker(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        ensure_model_exists()
        base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=2,
            min_hand_detection_confidence=0.65,
            min_hand_presence_confidence=0.65,
            min_tracking_confidence=0.65,
        )
        self.detector = vision.HandLandmarker.create_from_options(options)
        self.running = True

    def run(self):
        cap = cv2.VideoCapture(0)
        screen_w = user32.GetSystemMetrics(0)
        screen_h = user32.GetSystemMetrics(1)

        smooth_x, smooth_y = screen_w // 2, screen_h // 2
        last_raw_x, last_raw_y = smooth_x, smooth_y
        is_pinching = False
        last_click_time = 0

        active_mode = "AIR_MOUSE"
        mode_switch_start = None
        REQUIRED_HOLD_TIME = 1.0

        # Telekinesis cooldown timers
        last_desktop_wipe_time = 0.0
        last_volume_step_time = 0.0
        prev_rotary_angle = None
        last_explode_state = False

        while self.running and cap.isOpened():
            success, frame = cap.read()
            if not success:
                break

            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            detection_result = self.detector.detect(mp_image)

            num_hands = len(detection_result.hand_landmarks) if detection_result.hand_landmarks else 0
            payload = {
                "num_hands": num_hands,
                "active_mode": active_mode,
                "hands": [],
                "scale_delta": 1.0,
                "explode_val": 0.0,
                "locking_pct": 0.0,
                "volume_level": None,
            }

            if num_hands > 0:
                hands_data = []
                for landmarks in detection_result.hand_landmarks:
                    idx_tip = landmarks[8]
                    th_tip = landmarks[4]
                    mid_tip = landmarks[12]
                    rng_tip = landmarks[16]
                    pky_tip = landmarks[20]

                    norm_x, norm_y, norm_z = idx_tip.x, idx_tip.y, idx_tip.z
                    pinch_dist = math.hypot(idx_tip.x - th_tip.x, idx_tip.y - th_tip.y)
                    is_pinched = pinch_dist < 0.055

                    # Open Flat Palm check (all 5 fingers extended upward and spread)
                    is_flat_palm = (
                        idx_tip.y < landmarks[6].y
                        and mid_tip.y < landmarks[10].y
                        and rng_tip.y < landmarks[14].y
                        and pky_tip.y < landmarks[18].y
                        and pinch_dist > 0.10
                    )

                    # Peace Sign (Mode Lock Toggle)
                    is_peace = (
                        idx_tip.y < landmarks[6].y
                        and mid_tip.y < landmarks[10].y
                        and rng_tip.y > landmarks[14].y
                        and pky_tip.y > landmarks[18].y
                        and pinch_dist > 0.08
                    )

                    # Two-Finger Rotary Stance (Index + Middle extended close together)
                    is_rotary_stance = (
                        idx_tip.y < landmarks[6].y
                        and mid_tip.y < landmarks[10].y
                        and rng_tip.y > landmarks[14].y
                        and pky_tip.y > landmarks[18].y
                        and math.hypot(idx_tip.x - mid_tip.x, idx_tip.y - mid_tip.y) < 0.045
                    )

                    hands_data.append({
                        "norm_x": norm_x,
                        "norm_y": norm_y,
                        "norm_z": norm_z,
                        "is_pinched": is_pinched,
                        "is_peace": is_peace,
                        "is_flat_palm": is_flat_palm,
                        "is_rotary_stance": is_rotary_stance,
                        "screen_x": int(norm_x * screen_w),
                        "screen_y": int(norm_y * screen_h),
                        "palm_center": (int(landmarks[9].x * screen_w), int(landmarks[9].y * screen_h)),
                    })

                primary = hands_data[0]
                payload["hands"] = hands_data

                # --- 1. INSTANT GESTURE BARGE-IN INTERRUPT ---
                # Open palm facing camera immediately halts speaking J.A.R.V.I.S.
                if primary["is_flat_palm"] and is_speaking():
                    stop_speaking()
                    play_whoosh()

                # --- 2. DESKTOP TELEKINESIS: TWO-HANDED DESKTOP WIPE (Win + D) ---
                if num_hands >= 2 and hands_data[0]["is_flat_palm"] and hands_data[1]["is_flat_palm"]:
                    h1 = hands_data[0]["palm_center"]
                    h2 = hands_data[1]["palm_center"]
                    span = math.hypot(h1[0] - h2[0], h1[1] - h2[1])

                    if span > 580 and (time.time() - last_desktop_wipe_time) > 1.8:
                        win32_hotkey_win_d()
                        play_whoosh()
                        last_desktop_wipe_time = time.time()

                # --- 3. DESKTOP TELEKINESIS: ROTARY AIR VOLUME DIAL ---
                if primary["is_rotary_stance"] and active_mode == "AIR_MOUSE":
                    curr_angle = math.atan2(primary["norm_y"] - 0.5, primary["norm_x"] - 0.5)
                    if prev_rotary_angle is not None:
                        diff = curr_angle - prev_rotary_angle
                        # Account for radian boundary wrap
                        if diff > math.pi:
                            diff -= 2 * math.pi
                        elif diff < -math.pi:
                            diff += 2 * math.pi

                        if abs(diff) > 0.08 and (time.time() - last_volume_step_time) > 0.08:
                            is_vol_up = diff > 0
                            win32_volume_adjust(up=is_vol_up)
                            play_vol_tick("up" if is_vol_up else "down")
                            last_volume_step_time = time.time()
                    prev_rotary_angle = curr_angle
                else:
                    prev_rotary_angle = None

                # --- 4. MODE TOGGLE ENGINE WITH LOCK CHIME ---
                if primary["is_peace"] and num_hands == 1 and not primary["is_rotary_stance"]:
                    if mode_switch_start is None:
                        mode_switch_start = time.time()
                    held = time.time() - mode_switch_start
                    payload["locking_pct"] = min(1.0, held / REQUIRED_HOLD_TIME)
                    if held >= REQUIRED_HOLD_TIME:
                        active_mode = "3D_HOLOGRAM" if active_mode == "AIR_MOUSE" else "AIR_MOUSE"
                        mode_switch_start = None
                        play_lock()
                else:
                    mode_switch_start = None

                # --- 5. AIR MOUSE POINTER CONTROL ---
                if active_mode == "AIR_MOUSE" and not primary["is_rotary_stance"]:
                    raw_x, raw_y = primary["screen_x"], primary["screen_y"]
                    speed = math.hypot(raw_x - last_raw_x, raw_y - last_raw_y)
                    alpha = min(0.85, max(0.18, speed / 110.0))
                    smooth_x = int(alpha * raw_x + (1 - alpha) * smooth_x)
                    smooth_y = int(alpha * raw_y + (1 - alpha) * smooth_y)
                    last_raw_x, last_raw_y = raw_x, raw_y

                    if speed > 2.0:
                        user32.SetCursorPos(smooth_x, smooth_y)

                    if primary["is_pinched"]:
                        if not is_pinching and (time.time() - last_click_time) > 0.35:
                            user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                            user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                            last_click_time = time.time()
                            is_pinching = True
                            play_click()
                    else:
                        is_pinching = False

                # --- 6. TWO-HANDED SCALING & EXPLOSION SOUNDS ---
                elif active_mode == "3D_HOLOGRAM" and num_hands >= 2:
                    if hands_data[0]["is_pinched"] and hands_data[1]["is_pinched"]:
                        h1 = (hands_data[0]["screen_x"], hands_data[0]["screen_y"])
                        h2 = (hands_data[1]["screen_x"], hands_data[1]["screen_y"])
                        dist = math.hypot(h1[0] - h2[0], h1[1] - h2[1])
                        payload["scale_delta"] = dist / 380.0

                        if dist > 320:
                            payload["explode_val"] = min(1.0, (dist - 320) / 240.0)
                            if not last_explode_state:
                                play_explode()
                                last_explode_state = True
                        elif dist < 180 and last_explode_state:
                            play_snap()
                            last_explode_state = False

            if telemetry_queue.full():
                try:
                    telemetry_queue.get_nowait()
                except queue.Empty:
                    pass
            telemetry_queue.put(payload)
            time.sleep(0.015)

        cap.release()

    def stop(self):
        self.running = False


if __name__ == "__main__":
    tracker = HeadlessSpatialTracker()
    tracker.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        tracker.stop()