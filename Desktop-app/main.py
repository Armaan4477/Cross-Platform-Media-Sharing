import sys
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QApplication,
                             QHBoxLayout, QLabel, QFrame)
from PyQt6.QtGui import QScreen, QFont, QColor, QPainter, QPen, QBrush, QPixmap, QIcon
from PyQt6.QtCore import Qt, QSize, QTimer, QRect
from file_receiver import ReceiveApp
from file_sender import SendApp
from broadcast import Broadcast
from preferences import PreferencesApp
from credits_dialog import CreditsDialog
from constant import logger, get_config

# Placeholder for logger and get_config
import logging
logger = logging.getLogger(__name__)
def get_config():
    return {"save_to_directory": "received_files"}

class SophisticatedButton(QPushButton):
    def __init__(self, icon_path, text, parent=None):
        super().__init__(parent)
        self.setFixedSize(80, 80)
        if os.path.exists(icon_path):
            self.setIcon(QIcon(icon_path))
            self.setIconSize(QSize(40, 40))
        self.setText(text)
        self.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 10px;
                color: white;
                font-size: 12px;
                padding-top: 45px;
                text-align: bottom;
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
        self.setFixedSize(200, 200)
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

        # Draw WiFi signals moving upwards
        for i in range(3):
            radius = max_radius * (i + 1) // 3
            opacity = min(1, self.signal_strength / 100 * 3 - i)
            painter.setPen(QPen(QColor(255, 255, 255, int(opacity * 255)), 2))
            painter.drawArc(center.x() - radius, center.y() + max_radius // 2 - radius,
                            radius * 2, radius * 2, 180 * 16, 180 * 16)

class MainApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('DataDash')
        self.setGeometry(100, 100, 1280, 720)  # 16:9 ratio
        self.center_window()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Background
        self.setStyleSheet("""
            QWidget#mainWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                            stop:0 #45B3A8, stop:1 #3F8A9E);
            }
        """)
        self.setObjectName("mainWidget")

        # Header
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.2);
                border-bottom-left-radius: 20px;
                border-bottom-right-radius: 20px;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 10, 10, 10)

        # Preferences (3 dots)
        preferences_btn = QPushButton("⋮")
        preferences_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                font-size: 24px;
                border: none;
            }
        """)
        preferences_btn.clicked.connect(self.preferences_handler)
        header_layout.addWidget(preferences_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        # Logo and DataDash text
        logo_label = QLabel()
        logo_pixmap = QPixmap(32, 32)
        logo_pixmap.fill(Qt.GlobalColor.transparent)
        logo_painter = QPainter(logo_pixmap)
        logo_painter.setBrush(QBrush(QColor("#45B3A8")))
        logo_painter.drawEllipse(0, 0, 32, 32)
        logo_painter.end()
        logo_label.setPixmap(logo_pixmap)
        
        project_label = QLabel("DataDash")
        project_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        project_label.setStyleSheet("color: white;")

        logo_text_layout = QHBoxLayout()
        logo_text_layout.addWidget(logo_label)
        logo_text_layout.addWidget(project_label)
        logo_text_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addLayout(logo_text_layout)

        # Static Profile
        profile_label = QLabel()
        profile_pixmap = QPixmap(32, 32)
        profile_pixmap.fill(Qt.GlobalColor.lightGray)
        profile_painter = QPainter(profile_pixmap)
        profile_painter.setPen(Qt.PenStyle.NoPen)
        profile_painter.setBrush(QBrush(Qt.GlobalColor.darkGray))
        profile_painter.drawEllipse(0, 0, 32, 32)
        profile_painter.end()
        profile_label.setPixmap(profile_pixmap)
        header_layout.addWidget(profile_label, alignment=Qt.AlignmentFlag.AlignRight)

        main_layout.addWidget(header)

        # Buttons
        button_layout = QHBoxLayout()
        send_btn = SophisticatedButton("send_icon.png", "Send")
        receive_btn = SophisticatedButton("receive_icon.png", "Receive")
        send_btn.clicked.connect(self.send_handler)
        receive_btn.clicked.connect(self.receive_handler)
        
        button_layout.addWidget(send_btn)
        button_layout.addWidget(receive_btn)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addLayout(button_layout)

        main_layout.addStretch(1)  # Add stretch to push the WiFi animation to the bottom

        # WiFi Animation
        self.wifi_widget = WifiAnimationWidget(self)
        main_layout.addWidget(self.wifi_widget, 0, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)

        logger.info("Started DataDash App")

    def center_window(self):
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        window_width, window_height = 1280, 720
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2
        self.setGeometry(x, y, window_width, window_height)

        dest = get_config()["save_to_directory"]
        if not os.path.exists(dest):
            os.makedirs(dest)
            logger.info("Created folder to receive files")

    def local_files(self):
        logger.info("Accessed Local Files")
        # Implement local files functionality

    def sendFile(self):
        logger.info("Started Send File App")
        self.hide()
        self.broadcast_app = Broadcast()
        self.broadcast_app.show()

    def receiveFile(self):
        logger.info("Started Receive File App")
        self.hide()
        self.receive_app = ReceiveApp()
        self.receive_app.show()

    def invite_friends(self):
        logger.info("Invite Friends")
        # Implement invite friends functionality

    def preferences_handler(self):
        logger.info("Started Preferences handler menu")
        self.hide()
        self.preferences_app = PreferencesApp()
        self.preferences_app.show()

    def show_credits(self):
        logger.info("Opened Credits Dialog")
        credits_dialog = CreditsDialog()
        credits_dialog.exec()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main = MainApp()
    main.show()
    sys.exit(app.exec())