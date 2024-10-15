from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QApplication,
                             QLabel, QFrame)
from PyQt6.QtGui import QScreen, QFont, QPalette, QBrush, QPixmap
from PyQt6.QtCore import Qt
from file_receiver import ReceiveApp
from file_sender import SendApp
from broadcast import Broadcast
from preferences import PreferencesApp
from credits_dialog import CreditsDialog
import sys
import os
from constant import logger, get_config

class MainApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Media Sharing App')
        self.setGeometry(100, 100, 800, 400)
        self.center_window()
        self.set_background()

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QFrame()
        header.setStyleSheet("background-color: #333; padding: 10px;")
        header_layout = QHBoxLayout(header)
        title_label = QLabel("Media Sharing App")
        title_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        title_label.setStyleSheet("color: white;")
        header_layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(header)

        # Buttons Layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(30)
        button_layout.setContentsMargins(50, 50, 50, 50)

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

        # Preferences Button
        self.preferences_button = QPushButton('Preferences')
        self.style_button(self.preferences_button)
        self.preferences_button.clicked.connect(self.preferences_handler)
        button_layout.addWidget(self.preferences_button)

        # Credits Button
        self.credits_button = QPushButton('Credits')
        self.style_button(self.credits_button)
        self.credits_button.clicked.connect(self.show_credits)
        button_layout.addWidget(self.credits_button)

        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)
        logger.info("Started Main App")

    def style_button(self, button):
        button.setFixedSize(150, 50)
        button.setFont(QFont("Arial", 12))
        button.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 120, 215, 0.6);
                color: white;
                border-radius: 12px;
                border: 2px solid #005bb5;
                padding: 10px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: rgba(0, 91, 181, 0.8);
            }
            QPushButton:pressed {
                background-color: rgba(0, 120, 215, 0.6);
            }
        """)

    def set_background(self):
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, Qt.GlobalColor.lightGray)
        self.setPalette(palette)
        self.setAutoFillBackground(True)

    def center_window(self):
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        window_width, window_height = 800, 400
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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main = MainApp()
    main.show()
    sys.exit(app.exec())
