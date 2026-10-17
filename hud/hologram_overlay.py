import math
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import numpy as np
from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QWidget

from core.vision_hands import HeadlessSpatialTracker, telemetry_queue


class HolographicDesktopGlass(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.showFullScreen()

        self.active_mode = "AIR_MOUSE"
        self.active_primitive = 0  # 0: Cube, 1: Tesseract, 2: Arc Reactor, 3: 3D Draw
        self.primitive_names = ["MODULAR CUBE", "4D TESSERACT", "ARC REACTOR", "3D LIGHT CANVAS"]

        self.angle_x = 20.0
        self.angle_y = 35.0
        self.scale = 1.0
        self.explosion_factor = 0.0
        self.locking_pct = 0.0
        self.hands_telemetry = []

        self.last_grab_x = None
        self.last_grab_y = None

        # Build Geometry
        self._init_cube()
        self._init_tesseract()
        self.arc_spin = 0.0

        # 3D Drawing Canvas Data
        self.strokes = []
        self.current_stroke = []

        # Virtual Mid-Air Toolbar Rectangles
        w = self.width()
        start_x = w // 2 - 320
        self.buttons = [
            {"id": 0, "label": "CUBE", "rect": QRectF(start_x, 25, 110, 36)},
            {"id": 1, "label": "TESSERACT", "rect": QRectF(start_x + 120, 25, 130, 36)},
            {"id": 2, "label": "ARC REACTOR", "rect": QRectF(start_x + 260, 25, 140, 36)},
            {"id": 3, "label": "3D DRAW", "rect": QRectF(start_x + 410, 25, 110, 36)},
            {"id": 9, "label": "CLEAR", "rect": QRectF(start_x + 530, 25, 100, 36)},
        ]
        self.last_btn_click = 0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_telemetry_and_paint)
        self.timer.start(16)

    def _init_cube(self):
        s = 85.0
        self.cube_faces = [
            {"v": np.array([[-s, -s, s], [s, -s, s], [s, s, s], [-s, s, s]]), "norm": np.array([0, 0, 1.0])},
            {"v": np.array([[-s, -s, -s], [s, -s, -s], [s, s, -s], [-s, s, -s]]), "norm": np.array([0, 0, -1.0])},
            {"v": np.array([[-s, -s, -s], [s, -s, -s], [s, -s, s], [-s, -s, s]]), "norm": np.array([0, -1.0, 0])},
            {"v": np.array([[-s, s, -s], [s, s, -s], [s, s, s], [-s, s, s]]), "norm": np.array([0, 1.0, 0])},
            {"v": np.array([[-s, -s, -s], [-s, s, -s], [-s, s, s], [-s, -s, s]]), "norm": np.array([-1.0, 0, 0])},
            {"v": np.array([[s, -s, -s], [s, s, -s], [s, s, s], [s, -s, s]]), "norm": np.array([1.0, 0, 0])},
        ]
        d = 45.0
        self.cube_diamond = np.array([
            [0, -d, 0], [d, 0, 0], [0, d, 0], [-d, 0, 0], [0, 0, -d], [0, 0, d]
        ], dtype=float)
        self.cube_diamond_edges = [
            (0, 1), (1, 2), (2, 3), (3, 0), (4, 0), (4, 1),
            (4, 2), (4, 3), (5, 0), (5, 1), (5, 2), (5, 3)
        ]

    def _init_tesseract(self):
        verts = []
        for x in (-1, 1):
            for y in (-1, 1):
                for z in (-1, 1):
                    for w_val in (-1, 1):
                        verts.append([x, y, z, w_val])
        self.tesseract_verts = np.array(verts, dtype=float) * 65.0
        self.tesseract_edges = []
        for i in range(16):
            for j in range(i + 1, 16):
                if np.sum(np.abs(self.tesseract_verts[i] - self.tesseract_verts[j]) > 0.1) == 1:
                    self.tesseract_edges.append((i, j))
        self.angle_4d = 0.0

    def update_telemetry_and_paint(self):
        import time
        if not telemetry_queue.empty():
            data = telemetry_queue.get()
            self.active_mode = data.get("active_mode", "AIR_MOUSE")
            self.hands_telemetry = data.get("hands", [])
            self.locking_pct = data.get("locking_pct", 0.0)

            if self.active_mode == "3D_HOLOGRAM":
                # Only update scaling when actively two-hand pinching
                if data.get("scale_delta", 1.0) != 1.0:
                    self.scale = max(0.4, min(2.5, data["scale_delta"]))

                # LATCHED EXPLOSION LOGIC:
                # If both hands are actively pulling apart, update explosion value
                new_explode = data.get("explode_val", None)
                if len(self.hands_telemetry) >= 2:
                    h1_pinched = self.hands_telemetry[0].get("is_pinched", False)
                    h2_pinched = self.hands_telemetry[1].get("is_pinched", False)

                    if h1_pinched and h2_pinched:
                        h1 = (self.hands_telemetry[0]["screen_x"], self.hands_telemetry[0]["screen_y"])
                        h2 = (self.hands_telemetry[1]["screen_x"], self.hands_telemetry[1]["screen_y"])
                        dist = math.hypot(h1[0] - h2[0], h1[1] - h2[1])

                        if dist > 320:
                            # Expand facets outward and hold the state
                            self.explosion_factor = min(1.0, (dist - 320) / 240.0)
                        elif dist < 180:
                            # Reassembly zone: pushing hands close together snaps facets shut
                            self.explosion_factor = 0.0
                # When hands release, self.explosion_factor is NOT reset; it stays frozen in place
                # Check UI Button selections
                if self.hands_telemetry:
                    p_hand = self.hands_telemetry[0]
                    hx, hy = p_hand["screen_x"], p_hand["screen_y"]

                    for btn in self.buttons:
                        if btn["id"] == 9 and self.active_primitive != 3:
                            continue
                        if btn["rect"].contains(QPointF(hx, hy)):
                            if p_hand.get("is_pinched") and (time.time() - self.last_btn_click) > 0.4:
                                from core.audio_fx import play_click
                                play_click()
                                if btn["id"] == 9:
                                    self.strokes = []
                                    self.current_stroke = []
                                else:
                                    self.active_primitive = btn["id"]
                                self.last_btn_click = time.time()

                # Single-Hand Manipulations or Drawing
                if len(self.hands_telemetry) == 1:
                    h = self.hands_telemetry[0]
                    hx, hy = h["screen_x"], h["screen_y"]
                    is_p = h.get("is_pinched", False)

                    if self.active_primitive == 3:  # 3D DRAW
                        cx, cy = self.width() // 2, self.height() // 2
                        rad_x, rad_y = math.radians(self.angle_x), math.radians(self.angle_y)
                        rot_x = np.array([[1, 0, 0], [0, math.cos(rad_x), -math.sin(rad_x)], [0, math.sin(rad_x), math.cos(rad_x)]])
                        rot_y = np.array([[math.cos(rad_y), 0, math.sin(rad_y)], [0, 1, 0], [-math.sin(rad_y), 0, math.cos(rad_y)]])

                        if is_p and hy > 70:
                            dx = (hx - cx) / self.scale
                            dy = (hy - cy) / self.scale
                            dz = h.get("norm_z", 0.0) * 200.0
                            pt = np.array([dx, dy, dz]) @ rot_x @ rot_y
                            self.current_stroke.append(pt)
                        else:
                            if len(self.current_stroke) > 1:
                                self.strokes.append(np.array(self.current_stroke))
                            self.current_stroke = []
                    else:  # GRAB & ROTATE
                        if is_p and hy > 70:
                            if self.last_grab_x is not None:
                                dx = hx - self.last_grab_x
                                dy = hy - self.last_grab_y
                                self.angle_y += dx * 0.45
                                self.angle_x -= dy * 0.45
                            self.last_grab_x = hx
                            self.last_grab_y = hy
                        else:
                            self.last_grab_x = None
                            self.last_grab_y = None
                            self.angle_y += 0.3
                            self.angle_x += 0.1
                else:
                    self.last_grab_x = None
                    self.last_grab_y = None
                    self.angle_y += 0.3
                    self.angle_x += 0.1

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2

        # 1. Floating Hologram Viewport
        if self.active_mode == "3D_HOLOGRAM":
            rad_x, rad_y = math.radians(self.angle_x), math.radians(self.angle_y)
            rot_x = np.array([[1, 0, 0], [0, math.cos(rad_x), -math.sin(rad_x)], [0, math.sin(rad_x), math.cos(rad_x)]])
            rot_y = np.array([[math.cos(rad_y), 0, math.sin(rad_y)], [0, 1, 0], [-math.sin(rad_y), 0, math.cos(rad_y)]])

            if self.active_primitive == 0:
                self.paint_cube(painter, cx, cy, rot_x, rot_y)
            elif self.active_primitive == 1:
                self.paint_tesseract(painter, cx, cy, rot_x, rot_y)
            elif self.active_primitive == 2:
                self.paint_arc_reactor(painter, cx, cy, rot_x, rot_y)
            elif self.active_primitive == 3:
                self.paint_light_draw(painter, cx, cy, rot_x, rot_y)

            # Paint Floating Virtual Header Buttons
            self.paint_toolbar(painter)

        # 2. Hand Reticles & Locking Ring
        for hand in self.hands_telemetry:
            hx, hy = hand["screen_x"], hand["screen_y"]
            reticle_color = QColor(255, 60, 60) if hand.get("is_pinched") else QColor(0, 255, 220)

            painter.setPen(QPen(reticle_color, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(hx, hy), 12, 12)
            painter.drawEllipse(QPointF(hx, hy), 3, 3)

            if self.locking_pct > 0.0:
                painter.setPen(QPen(QColor(255, 200, 0), 3))
                span = int(self.locking_pct * 360 * 16)
                painter.drawArc(QRectF(hx - 32, hy - 32, 64, 64), 90 * 16, -span)

        # 3. Status Badge (Top-Left)
        badge_text = (
            "MARK-IV // AIR MOUSE [ACTIVE]"
            if self.active_mode == "AIR_MOUSE"
            else f"MARK-IV // 3D GLASS [{self.primitive_names[self.active_primitive]}]"
        )
        badge_color = QColor(0, 255, 120) if self.active_mode == "AIR_MOUSE" else QColor(0, 220, 255)

        painter.setPen(QPen(badge_color, 1))
        painter.setBrush(QColor(10, 15, 25, 200))
        painter.drawRoundedRect(QRectF(30, 25, 360, 36), 6, 6)

        painter.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        painter.setPen(badge_color)
        painter.drawText(QRectF(45, 25, 340, 36), int(Qt.AlignmentFlag.AlignVCenter), badge_text)

    def paint_toolbar(self, painter):
        for btn in self.buttons:
            if btn["id"] == 9 and self.active_primitive != 3:
                continue
            is_active = btn["id"] == self.active_primitive
            fill_col = QColor(0, 180, 255, 60) if is_active else QColor(10, 15, 25, 200)
            border_col = QColor(0, 255, 255) if is_active else QColor(80, 100, 120)

            painter.setBrush(fill_col)
            painter.setPen(QPen(border_col, 1.5))
            painter.drawRoundedRect(btn["rect"], 5, 5)

            painter.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
            painter.setPen(QColor(255, 255, 255) if is_active else QColor(180, 190, 200))
            painter.drawText(btn["rect"], int(Qt.AlignmentFlag.AlignCenter), btn["label"])

    def paint_cube(self, painter, cx, cy, rot_x, rot_y):
        fov = 550
        explode_d = 85.0 * 0.9 * self.explosion_factor
        cube_col = QColor(255, 140, 0, 220) if self.explosion_factor > 0.1 else QColor(0, 240, 255, 220)

        for face in self.cube_faces:
            shifted = face["v"] + (face["norm"] * explode_d)
            trans = (shifted * self.scale) @ rot_x.T @ rot_y.T
            pts = []
            for x, y, z in trans:
                sc = fov / max(z + 500, 1)
                pts.append(QPointF(x * sc + cx, y * sc + cy))

            painter.setPen(QPen(cube_col, 2))
            for i in range(4):
                painter.drawLine(pts[i], pts[(i + 1) % 4])

        # Core diamond
        core_trans = (self.cube_diamond * self.scale) @ rot_x @ rot_y.T
        diamond_pts = []
        for x, y, z in core_trans:
            sc = fov / max(z + 500, 1)
            diamond_pts.append(QPointF(x * sc + cx, y * sc + cy))

        painter.setPen(QPen(QColor(0, 255, 180, 180), 1))
        for p1, p2 in self.cube_diamond_edges:
            painter.drawLine(diamond_pts[p1], diamond_pts[p2])

    def paint_tesseract(self, painter, cx, cy, rot_x, rot_y):
        self.angle_4d += 0.02
        rad_w = self.angle_4d
        rot_4d = np.array([
            [math.cos(rad_w), 0, 0, -math.sin(rad_w)],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [math.sin(rad_w), 0, 0, math.cos(rad_w)],
        ])
        rot_4 = self.tesseract_verts @ rot_4d.T

        dist_4d = 180.0
        proj_3d = []
        for x, y, z, w_val in rot_4:
            sc = dist_4d / max(dist_4d - w_val, 1)
            proj_3d.append([x * sc, y * sc, z * sc])
        trans = np.array(proj_3d) * self.scale @ rot_x.T @ rot_y.T

        fov = 550
        pts = [QPointF(x * (fov / max(z + 500, 1)) + cx, y * (fov / max(z + 500, 1)) + cy) for x, y, z in trans]

        painter.setPen(QPen(QColor(0, 240, 255, 210), 2))
        for p1, p2 in self.tesseract_edges:
            painter.drawLine(pts[p1], pts[p2])
        painter.setBrush(QColor(255, 0, 220))
        painter.setPen(Qt.PenStyle.NoPen)
        for pt in pts:
            painter.drawEllipse(pt, 3.0, 3.0)

    def paint_arc_reactor(self, painter, cx, cy, rot_x, rot_y):
        self.arc_spin += 2.0
        rad_s = math.radians(self.arc_spin)
        fov = 550

        configs = [
            (110 * self.scale, QColor(0, 255, 255), rad_s, 0.0),
            (85 * self.scale, QColor(0, 200, 255), -rad_s * 1.3, math.pi / 4),
            (60 * self.scale, QColor(0, 140, 255), rad_s * 1.8, math.pi / 2),
        ]
        for r, col, spin_off, tilt_off in configs:
            pts_3d = []
            steps = 28
            for i in range(steps):
                th = (2 * math.pi / steps) * i
                pts_3d.append([r * math.cos(th), r * math.sin(th) * math.cos(tilt_off), r * math.sin(th) * math.sin(tilt_off)])

            rot_z = np.array([[math.cos(spin_off), -math.sin(spin_off), 0], [math.sin(spin_off), math.cos(spin_off), 0], [0, 0, 1]])
            trans = np.array(pts_3d) @ rot_z.T @ rot_x.T @ rot_y.T
            pts = [QPointF(x * (fov / max(z + 500, 1)) + cx, y * (fov / max(z + 500, 1)) + cy) for x, y, z in trans]

            painter.setPen(QPen(col, 2))
            for i in range(len(pts)):
                painter.drawLine(pts[i], pts[(i + 1) % len(pts)])

        # Center Palladium Core
        painter.setBrush(QColor(255, 255, 255))
        painter.setPen(QPen(QColor(0, 255, 255), 2))
        painter.drawEllipse(QPointF(cx, cy), 16 * self.scale, 16 * self.scale)

    def paint_light_draw(self, painter, cx, cy, rot_x, rot_y):
        fov = 550
        all_s = self.strokes + ([np.array(self.current_stroke)] if len(self.current_stroke) > 1 else [])

        painter.setPen(QPen(QColor(0, 255, 180, 220), 2.5))
        for stroke in all_s:
            trans = (stroke * self.scale) @ rot_x.T @ rot_y.T
            pts = [QPointF(x * (fov / max(z + 500, 1)) + cx, y * (fov / max(z + 500, 1)) + cy) for x, y, z in trans]
            for i in range(len(pts) - 1):
                painter.drawLine(pts[i], pts[i + 1])


if __name__ == "__main__":
    app = QApplication(sys.argv)
    tracker = HeadlessSpatialTracker()
    tracker.start()

    overlay = HolographicDesktopGlass()
    try:
        sys.exit(app.exec())
    finally:
        tracker.stop()