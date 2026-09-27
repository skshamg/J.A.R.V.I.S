from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt6.QtCore import Qt


def create_reactor_icon() -> QIcon:
    """Generates a dynamic 32x32 glowing cyan Arc Reactor icon for the Windows tray."""
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Outer cyan ring
    painter.setPen(QColor(0, 240, 255, 220))
    painter.setBrush(QColor(8, 14, 26))
    painter.drawEllipse(2, 2, 28, 28)

    # Inner glowing core
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(0, 240, 255))
    painter.drawEllipse(10, 10, 12, 12)

    painter.end()
    return QIcon(pixmap)


class JarvisSystemTray(QSystemTrayIcon):
    def __init__(self, hud_window, parent=None):
        super().__init__(parent)
        self.hud = hud_window

        self.setIcon(create_reactor_icon())
        self.setToolTip("J.A.R.V.I.S. // Autonomous Agent Core")

        self._build_menu()
        self.activated.connect(self._on_tray_clicked)
        self.show()

    def _build_menu(self):
        menu = QMenu()

        toggle_action = menu.addAction("Toggle HUD")
        toggle_action.triggered.connect(self.toggle_hud_visibility)

        menu.addSeparator()

        exit_action = menu.addAction("Shut Down J.A.R.V.I.S.")
        exit_action.triggered.connect(QApplication.instance().quit)

        self.setContextMenu(menu)

    def toggle_hud_visibility(self):
        """Safely toggles visibility on the main Qt thread."""
        if self.hud.isVisible():
            self.hud.hide()
        else:
            self.hud.show()
            self.hud.raise_()
            self.hud.activateWindow()

    def _on_tray_clicked(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.toggle_hud_visibility()