from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QApplication,
                             QLabel, QFrame, QGraphicsDropShadowEffect)
from PyQt6.QtGui import QScreen, QFont, QPalette, QPainter, QColor, QPen, QIcon
from PyQt6.QtCore import Qt, QTimer, QSize
import sys
import os
from file_receiver import ReceiveApp
from file_sender import SendApp
from broadcast import Broadcast
from preferences import PreferencesApp
from credits_dialog import CreditsDialog
from constant import logger, get_config

class WifiAnimationWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(300, 250)
        self.signal_strength = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_signal)
        self.timer.start(35)

    def update_signal(self):
        self.signal_strength = (self.signal_strength + 1) % 100
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center = self.rect().center()
        max_radius = min(self.width(), self.height()) // 2

        for i in range(3):
            radius = max_radius * (i + 1) // 3
            opacity = min(1, self.signal_strength / 100 * 3 - i)
            painter.setPen(QPen(QColor(255, 255, 255, int(opacity * 255)), 2))
            painter.drawArc(center.x() - radius, center.y() - max_radius // 2 - radius,
                            radius * 2, radius * 2, 0, 180 * 16)

class MainApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.setFixedSize(700, 500)

    def initUI(self):
        self.setWindowTitle('DataDash')
        self.setGeometry(100, 100, 700, 500)
        self.center_window()
        self.set_background()

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QFrame()
        header.setFixedHeight(70)
        header.setStyleSheet("background-color: #333; padding: 0px;")
        header_layout = QHBoxLayout(header)

        # Define the relative path for the icon
        icon_path = os.path.join(os.path.dirname(__file__), "icons", "settings-icon.svg")

        # Settings Button with SVG icon
        self.settings_button = QPushButton()
        self.settings_button.setIcon(QIcon(icon_path))
        self.settings_button.setIconSize(QSize(32, 32))
        self.settings_button.setStyleSheet("border: none;")
        self.settings_button.clicked.connect(self.openSettings)
        header_layout.addWidget(self.settings_button, alignment=Qt.AlignmentFlag.AlignLeft)

        # Add a stretch after the settings button
        header_layout.addStretch()

        # Title label
        title_label = QLabel("DataDash: CrossPlatform Data Sharing")
        title_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        title_label.setStyleSheet("color: white;")
        header_layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Add another stretch after the title to balance the layout
        header_layout.addStretch()

        main_layout.addWidget(header)

        # Add some vertical space before the WiFi Animation Widget
        main_layout.addSpacing(50)

        # Wifi Animation Widget
        wifi_widget = WifiAnimationWidget()
        main_layout.addWidget(wifi_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        # Buttons Layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)  # Reduced spacing between Send and Receive buttons
        button_layout.setContentsMargins(40, 0, 40, 0)

        # Send File Button
        self.send_button = QPushButton('Send File')
        self.style_button(self.send_button)
        self.send_button.clicked.connect(self.sendFile)
        button_layout.addWidget(self.send_button)

        # Receive File Button
        self.receive_button = QPushButton('Receive File')
        self.style_button(self.receive_button)
        self.receive_button.clicked.connect(self.receiveFile)
        button_layout.addWidget(self.receive_button)

        # Add the first button layout to the main layout
        main_layout.addLayout(button_layout)

        # Add some vertical space above the Credits button layout
        main_layout.addSpacing(15)  # Moves buttons up and adds spacing between buttons and Credits

        # Add a separate layout for the Credits button
        credits_layout = QHBoxLayout()
        credits_layout.setContentsMargins(0, 0, 10, 20)  # Space below Credits button
        credits_layout.addStretch()  # Center the Credits button horizontally

        # Credits Button
        self.credits_button = QPushButton('Credits')
        self.style_button(self.credits_button)
        self.credits_button.clicked.connect(self.show_credits)
        credits_layout.addWidget(self.credits_button, alignment=Qt.AlignmentFlag.AlignCenter)

        credits_layout.addStretch()
        main_layout.addLayout(credits_layout)

        self.setLayout(main_layout)
        logger.info("Started Main App")



    def style_button(self, button):
        button.setFixedSize(150, 50)
        button.setFont(QFont("Arial", 15))
        button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(47, 54, 66, 255),
                    stop: 1 rgba(75, 85, 98, 255)
                );
                color: white;
                border-radius: 25px;
                border: 1px solid rgba(0, 0, 0, 0.5);
                padding: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(60, 68, 80, 255),
                    stop: 1 rgba(90, 100, 118, 255)
                );
            }
            QPushButton:pressed {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(35, 41, 51, 255),
                    stop: 1 rgba(65, 75, 88, 255)
                );
            }
        """)

        glow_effect = QGraphicsDropShadowEffect()
        glow_effect.setBlurRadius(15)
        glow_effect.setXOffset(0)
        glow_effect.setYOffset(0)
        glow_effect.setColor(QColor(255, 255, 255, 100))
        button.setGraphicsEffect(glow_effect)

    def set_background(self):
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #b0b0b0,
                    stop: 1 #505050
                );
            }
        """)

    def center_window(self):
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        window_width, window_height = 700, 500
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2
        self.setGeometry(x, y, window_width, window_height)

        dest = get_config()["save_to_directory"]
        if not os.path.exists(dest):
            os.makedirs(dest)
            logger.info("Created folder to receive files")

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

    def preferences_handler(self):
        logger.info("Started Preferences handler menu")
        self.hide()
        self.preferences_app = PreferencesApp()
        self.preferences_app.show()

    def show_credits(self):
        logger.info("Opened Credits Dialog")
        credits_dialog = CreditsDialog()
        credits_dialog.exec()

    def openSettings(self):
        logger.info("Settings button clicked")
        self.preferences_handler()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main = MainApp()
    main.show()
    sys.exit(app.exec())
