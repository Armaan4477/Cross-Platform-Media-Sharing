from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QApplication,
                             QHBoxLayout, QLabel, QFrame, QGraphicsOpacityEffect)
from PyQt6.QtGui import QScreen, QFont, QColor, QPainter, QPen, QBrush
from PyQt6.QtCore import Qt, QSize, QTimer, QPropertyAnimation, QEasingCurve
from file_receiver import ReceiveApp
from file_sender import SendApp
from broadcast import Broadcast
from preferences import PreferencesApp
from credits_dialog import CreditsDialog
import sys
import os
from constant import logger, get_config

class SophisticatedButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFixedSize(80, 40)
        self.setFont(QFont("Arial", 10))
        self.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 5px;
                color: white;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.3);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)

class WifiAnimationWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(300, 300)
        self.signal_strength = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_signal)
        self.timer.start(50)

    def update_signal(self):
        self.signal_strength = (self.signal_strength + 1) % 100
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center = self.rect().center()
        max_radius = min(self.width(), self.height()) // 2

        # Draw WiFi signals
        for i in range(3):
            radius = max_radius * (i + 1) // 3
            opacity = min(1, self.signal_strength / 100 * 3 - i)
            painter.setPen(QPen(QColor(255, 255, 255, int(opacity * 100)), 2))
            painter.drawArc(center.x() - radius, center.y() - radius,
                            radius * 2, radius * 2, 0, 180 * 16)

        # Draw profile picture placeholder
        profile_radius = max_radius // 4
        painter.setBrush(QBrush(QColor(200, 200, 200)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, profile_radius, profile_radius)
        
class MainApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('DataDash')
        self.setGeometry(100, 100, 360, 640)
        self.center_window()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Background
        self.setStyleSheet("""
            QWidget#mainWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                            stop:0 #1a237e, stop:1 #4a148c);
            }
        """)
        self.setObjectName("mainWidget")

        # Header with buttons
        header = QFrame()
        header.setStyleSheet("background-color: rgba(255, 255, 255, 0.1);")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 10, 10, 10)
        header_layout.setSpacing(10)

        buttons = ["Send", "Receive", "Preferences", "Credits"]
        for text in buttons:
            btn = SophisticatedButton(text)
            btn.clicked.connect(getattr(self, f"{text.lower()}_handler"))
            header_layout.addWidget(btn)

        main_layout.addWidget(header)

        # WiFi Animation
        self.wifi_widget = WifiAnimationWidget(self)
        main_layout.addWidget(self.wifi_widget, 1, Qt.AlignmentFlag.AlignCenter)

        # Project Name
        project_label = QLabel("DataDash")
        project_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        project_label.setStyleSheet("color: white; margin-top: 20px;")
        project_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(project_label)

        logger.info("Started DataDash App")

    def center_window(self):
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        window_width, window_height = 360, 640
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2
        self.setGeometry(x, y, window_width, window_height)

        dest = get_config()["save_to_directory"]
        if not os.path.exists(dest):
            os.makedirs(dest)
            logger.info("Created folder to receive files")

    def send_handler(self):
        logger.info("Started Send File App")
        self.hide()
        self.broadcast_app = Broadcast()
        self.broadcast_app.show()

    def receive_handler(self):
        logger.info("Started Receive File App")
        self.hide()
        self.receive_app = ReceiveApp()
        self.receive_app.show()

    def preferences_handler(self):
        logger.info("Started Preferences handler menu")
        self.hide()
        self.preferences_app = PreferencesApp()
        self.preferences_app.show()

    def credits_handler(self):
        logger.info("Opened Credits Dialog")
        credits_dialog = CreditsDialog()
        credits_dialog.exec()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main = MainApp()
    main.show()
    sys.exit(app.exec())