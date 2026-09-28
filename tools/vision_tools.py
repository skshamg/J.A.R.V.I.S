import io
import json
import os
import re
import pyautogui
from PIL import ImageGrab
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.02

# Cached connection pool to eliminate SSL handshake latency
_vision_client = None


def get_vision_client():
    global _vision_client
    if _vision_client is None:
        _vision_client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=10000)
        )
    return _vision_client


def click_element_on_screen(element_description: str) -> str:
    """
    Locates an on-screen UI element using low-latency spatial vision
    and clicks it with sub-pixel Windows scaling compensation.
    """
    try:
        # 1. Capture screen & map PyAutoGUI's virtual desktop canvas
        screen = ImageGrab.grab()
        pag_w, pag_h = pyautogui.size()
        orig_w, orig_h = screen.size

        # 2. Compress to 1280px max (<90KB) for instant network transmission
        scale = min(1280.0 / orig_w, 1.0)
        if scale < 1.0:
            target_dim = (int(orig_w * scale), int(orig_h * scale))
            scaled = screen.resize(target_dim)
        else:
            scaled = screen

        img_byte_arr = io.BytesIO()
        scaled.save(img_byte_arr, format="JPEG", quality=70)
        img_part = types.Part.from_bytes(data=img_byte_arr.getvalue(), mime_type="image/jpeg")

        client = get_vision_client()

        prompt = f"""
Find the UI element: "{element_description}".
Return ONLY a JSON array with normalized bounding box coordinates on a 0 to 1000 scale:
[ymin, xmin, ymax, xmax]
If not visible, return: null
Output raw JSON only.
"""

        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=[prompt, img_part],
        )

        clean_json = re.sub(r"```(json)?", "", response.text.strip()).strip()

        if not clean_json or clean_json == "null":
            return f"Element '{element_description}' not found on screen."

        box = json.loads(clean_json)
        if not isinstance(box, list) or len(box) != 4:
            return f"Could not parse location for '{element_description}'."

        ymin, xmin, ymax, xmax = box

        # 3. Map directly to PyAutoGUI virtual coordinate space
        center_x_norm = (xmin + xmax) / 2.0
        center_y_norm = (ymin + ymax) / 2.0

        target_x = int((center_x_norm / 1000.0) * pag_w)
        target_y = int((center_y_norm / 1000.0) * pag_h)

        # 4. Snap cursor and click
        pyautogui.moveTo(target_x, target_y, duration=0.08)
        pyautogui.click(target_x, target_y)

        return f"Clicked '{element_description}' at ({target_x}, {target_y})."

    except Exception as e:
        return f"Visual click failed: {e}"