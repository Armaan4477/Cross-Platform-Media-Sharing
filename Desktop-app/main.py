from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QApplication,
                             QHBoxLayout, QLabel, QFrame, QScrollArea)
from PyQt6.QtGui import QScreen, QIcon, QFont
from PyQt6.QtCore import Qt, QSize
from file_receiver import ReceiveApp
from file_sender import SendApp
from broadcast import Broadcast
from preferences import PreferencesApp
from credits_dialog import CreditsDialog
import sys
import os
from constant import logger, get_config

class IconButton(QPushButton):
    def __init__(self, icon_path, text, parent=None):
        super().__init__(parent)
        self.setIcon(QIcon(icon_path))
        self.setIconSize(QSize(40, 40))
        self.setText(text)
        self.setFixedSize(80, 80)
        self.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border-radius: 10px;
                font-size: 12px;
                color: #333;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)

class MainApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('SHAREit')
        self.setGeometry(100, 100, 360, 640)
        self.center_window()

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setStyleSheet("background-color: white;")
        header_layout = QHBoxLayout(header)
        menu_button = QPushButton("≡")
        menu_button.setStyleSheet("font-size: 24px; border: none;")
        title_label = QLabel("SHAREit")
        title_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        profile_button = QPushButton("👤")
        profile_button.setStyleSheet("font-size: 24px; border: none;")
        header_layout.addWidget(menu_button)
        header_layout.addWidget(title_label, 1, Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(profile_button)
        main_layout.addWidget(header)

        # Scrollable content area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("background-color: #f5f5f5; border: none;")
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        # Icon buttons
        icon_layout = QHBoxLayout()
        icons = [
            ("icons/folder.png", "Local", self.local_files),
            ("icons/send.png", "Send", self.sendFile),
            ("icons/receive.png", "Receive", self.receiveFile),
            ("icons/invite.png", "Invite", self.invite_friends)
        ]
        for icon, text, func in icons:
            btn = IconButton(icon, text)
            btn.clicked.connect(func)
            icon_layout.addWidget(btn)
        scroll_layout.addLayout(icon_layout)

        # Video buffering section
        video_frame = QFrame()
        video_frame.setStyleSheet("""
            background-color: white;
            border-radius: 10px;
            margin: 10px;
        """)
        video_layout = QVBoxLayout(video_frame)
        video_title = QLabel("Video Buffering")
        video_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        video_desc = QLabel("See video without the network")
        video_desc.setStyleSheet("color: #666;")
        video_layout.addWidget(video_title)
        video_layout.addWidget(video_desc)
        # Add video thumbnail and details here
        scroll_layout.addWidget(video_frame)

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        self.setLayout(main_layout)
        logger.info("Started Main App")

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