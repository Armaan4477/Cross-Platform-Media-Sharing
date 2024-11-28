from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QApplication,
                             QLabel, QFrame, QGraphicsDropShadowEffect, QMessageBox)
from PyQt6.QtGui import QScreen, QFont, QColor, QIcon, QMovie
from PyQt6.QtCore import Qt, QTimer, QSize, QThread, pyqtSignal
import sys
import os
from file_receiver import ReceiveApp
from broadcast import Broadcast
from preferences import PreferencesApp
from constant import logger, get_config, PLATFORM_LINK
import platform
import requests
import ctypes

class VersionCheck(QThread):
    update_available = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.uga_version = None

    def run(self):
        self.currentversion()
        fetched_version = self.fetch_platform_value()
        if fetched_version and self.compare_versions(fetched_version, self.uga_version) > 0:
            self.update_available.emit()

    def fetch_platform_value(self):
        url = PLATFORM_LINK
        logger.info(f"Fetching platform value from: {url}")
        
        try:
            response = requests.get(url)
            response.raise_for_status()

            data = response.json()
            if "value" in data:
                logger.info(f"Value for python: {data['value']}")
                return data['value']
            else:
                logger.error(f"Value key not found in response: {data}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching platform value: {e}")
            return None

    def compare_versions(self, v1, v2):
        v1_parts = [int(part) for part in v1.split('.')]
        v2_parts = [int(part) for part in v2.split('.')]
        
        # Pad the shorter version with zeros
        while len(v1_parts) < 4:
            v1_parts.append(0)
        while len(v2_parts) < 4:
            v2_parts.append(0)
        
        return (v1_parts > v2_parts) - (v1_parts < v2_parts)

    def currentversion(self):
        config= get_config()
        self.uga_version = config["app_version"]

class MainApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.setFixedSize(853, 480) 
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def initUI(self):
        self.setWindowTitle('DataDash')
        self.setGeometry(100, 100, 853, 480)
        self.center_window()
        self.set_background()
        self.version_thread = VersionCheck()
        self.version_thread.update_available.connect(self.showmsgbox)
        self.check_update()

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QFrame()
        header.setFixedHeight(70)
        header.setStyleSheet("background-color: #333; padding: 0px;")
        header_layout = QHBoxLayout(header)

        # Create and add the IconButton instead of using SvgButton
        # Settings button
        settings_button = QPushButton()
        settings_button.setFixedSize(44, 44)
        settings_icon_path = os.path.join(os.path.dirname(__file__), "icons", "settings.svg")
        settings_button.setIcon(QIcon(settings_icon_path))
        settings_button.setIconSize(QSize(32, 32))
        settings_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 30);
                border-radius: 21px;
            }
        """)
        settings_button.setToolTip("<b style='color: #FFA500; font-size: 14px;'>Settings</b><br><i style='font-size: 12px;'>Click to configure</i>")
        settings_button.clicked.connect(self.openSettings)

        glow_effect = QGraphicsDropShadowEffect()
        glow_effect.setBlurRadius(15)
        glow_effect.setXOffset(0)
        glow_effect.setYOffset(0)
        glow_effect.setColor(QColor(255, 255, 255, 100))
        settings_button.setGraphicsEffect(glow_effect)

        header_layout.addWidget(settings_button, alignment=Qt.AlignmentFlag.AlignLeft)

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

        # Reduce the vertical spacing before the GIF
        main_layout.addSpacing(50)  # Decrease spacing from 105 to 50

        # Wifi Animation Widget
        gif_label = QLabel()
        gif_label.setStyleSheet("background-color: transparent;")  # Add this line
        movie = QMovie(os.path.join(os.path.dirname(__file__), "assets", "wifi.gif"))
        gif_label.setMovie(movie)
        movie.setScaledSize(QSize(550, 500))  # Decrease height from 500 to 400
        movie.start()
        main_layout.addWidget(gif_label, alignment=Qt.AlignmentFlag.AlignCenter)

        icon_path_send = os.path.join(os.path.dirname(__file__), "icons", "send.svg")
        icon_path_receive = os.path.join(os.path.dirname(__file__), "icons", "receive.svg")


        # Buttons Layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)  # Reduced spacing between Send and Receive buttons
        button_layout.setContentsMargins(30, 0, 30, 0)

        # Send File Button
        self.send_button = QPushButton('Send File')
        self.send_button.setIcon(QIcon(icon_path_send))
        self.send_button.setIconSize(QSize(24, 24))  # Adjust icon size as needed
        self.style_button(self.send_button)
        self.send_button.clicked.connect(self.sendFile)
        self.send_button.setToolTip("<b style='color: #FFA500; font-size: 14px;'>Send File</b><br><i style='font-size: 12px;'>Send a folder or multiple files to another device</i>")
        button_layout.addWidget(self.send_button)

        # Receive File Button
        self.receive_button = QPushButton('Receive File')
        self.receive_button.setIcon(QIcon(icon_path_receive))
        self.receive_button.setIconSize(QSize(24, 24))  # Adjust icon size as needed
        self.style_button(self.receive_button)
        self.receive_button.clicked.connect(self.receiveFile)
        self.receive_button.setToolTip("<b style='color: #FFA500; font-size: 14px;'>Receive File</b><br><i style='font-size: 12px;'>Receive a folder or multiple files from another device</i>")
        button_layout.addWidget(self.receive_button)

        # Add the first button layout to the main layout
        main_layout.addLayout(button_layout)

        # Add some vertical space above the Credits button layout
        main_layout.addSpacing(20)  # Moves buttons up and adds spacing between buttons and Credits

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
        window_width, window_height = 853, 480  # Changed from 700 to 853 for 16:9 ratio
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2
        self.setGeometry(x, y, window_width, window_height)
        #com.an.Datadash
        dest = get_config()["save_to_directory"]
        if not os.path.exists(dest):
            os.makedirs(dest)
            logger.info("Created folder to receive files")

    def sendFile(self):
        # Check if warnings should be shown
        if get_config()["show_warning"]:
            send_dialog = QMessageBox(self)
            send_dialog.setWindowTitle("Note")
            send_dialog.setText("""Before starting the transfer, please ensure both the sender and receiver devices are connected to the same network.
            """)
            send_dialog.setIcon(QMessageBox.Icon.Warning)

            # Add buttons
            proceed_button = send_dialog.addButton("Proceed", QMessageBox.ButtonRole.AcceptRole)
            cancel_button = send_dialog.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)

            # Apply consistent styling with a gradient background and transparent text area
            send_dialog.setStyleSheet("""
                QMessageBox {
                    background: qlineargradient(
                        x1: 0, y1: 0, x2: 1, y2: 1,
                        stop: 0 #b0b0b0,
                        stop: 1 #505050
                    );
                    color: #FFFFFF;
                    font-size: 16px;
                }
                QLabel {
                    background-color: transparent;  /* Transparent text background */
                    font-size: 16px;
                }
                QPushButton {
                    background: qlineargradient(
                        x1: 0, y1: 0, x2: 1, y2: 0,
                        stop: 0 rgba(47, 54, 66, 255),
                        stop: 1 rgba(75, 85, 98, 255)
                    );
                    color: white;
                    border-radius: 10px;
                    border: 1px solid rgba(0, 0, 0, 0.5);
                    padding: 4px;
                    font-size: 16px;
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

            # Execute dialog and handle response
            send_dialog.exec()
            if send_dialog.clickedButton() == proceed_button:
                logger.info("Started Send File App")
                self.hide()
                self.broadcast_app = Broadcast()
                self.broadcast_app.show()
                #com.an.Datadash
        else:
            logger.info("Started Send File App without warning")
            self.hide()
            self.broadcast_app = Broadcast()
            self.broadcast_app.show()

    def receiveFile(self):
        # Check if warnings should be shown
        if get_config()["show_warning"]:
            receive_dialog = QMessageBox(self)
            receive_dialog.setWindowTitle("Note")
            receive_dialog.setText("""Before starting the transfer, please ensure both the sender and receiver devices are connected to the same network.
            """)
            receive_dialog.setIcon(QMessageBox.Icon.Warning)

            # Add buttons
            proceed_button = receive_dialog.addButton("Proceed", QMessageBox.ButtonRole.AcceptRole)
            cancel_button = receive_dialog.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)

            # Apply consistent styling with a gradient background and transparent text area
            receive_dialog.setStyleSheet("""
                QMessageBox {
                    background: qlineargradient(
                        x1: 0, y1: 0, x2: 1, y2: 1,
                        stop: 0 #b0b0b0,
                        stop: 1 #505050
                    );
                    color: #FFFFFF;
                    font-size: 16px;
                }
                QLabel {
                    background-color: transparent;  /* Transparent text background */
                    font-size: 16px;
                }
                QPushButton {
                    background: qlineargradient(
                        x1: 0, y1: 0, x2: 1, y2: 0,
                        stop: 0 rgba(47, 54, 66, 255),
                        stop: 1 rgba(75, 85, 98, 255)
                    );
                    color: white;
                    border-radius: 10px;
                    border: 1px solid rgba(0, 0, 0, 0.5);
                    padding: 4px;
                    font-size: 16px;
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

            # Execute dialog and handle response
            receive_dialog.exec()
            if receive_dialog.clickedButton() == proceed_button:
                logger.info("Started Receive File App")
                self.hide()
                self.receive_app = ReceiveApp()
                self.receive_app.show()
        else:
            logger.info("Started Receive File App without warning")
            self.hide()
            self.receive_app = ReceiveApp()
            self.receive_app.show()


    def preferences_handler(self):
        logger.info("Started Preferences handler menu")
        self.hide()
        self.preferences_app = PreferencesApp()
        self.preferences_app.show()

    def openSettings(self):
        logger.info("Settings button clicked")
        self.preferences_handler()

    def check_update(self):
        if get_config()["check_update"]:
            logger.info("Checking for updates")
            self.version_thread.start()
        else:
            logger.info("Update check disabled")

    def showmsgbox(self):
        message = "You are on an older version. Please update."
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Version Check")
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Open)

        open_button = msg_box.button(QMessageBox.StandardButton.Open)
        if open_button:
            open_button.setText("Open Settings")

        msg_box.setStyleSheet("""
            QMessageBox {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #b0b0b0,
                    stop: 1 #505050
                );
                color: #FFFFFF;
                font-size: 16px;
            }
            QLabel {
                background-color: transparent;
            }
            QPushButton {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(47, 54, 66, 255),
                    stop: 1 rgba(75, 85, 98, 255)
                );
                color: white;
                border-radius: 10px;
                border: 1px solid rgba(0, 0, 0, 0.5);
                padding: 4px;
                font-size: 16px;
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
        reply = msg_box.exec()

        if reply == QMessageBox.StandardButton.Open:
            self.openSettings()



if __name__ == '__main__':
    app = QApplication(sys.argv)
    if platform.system() == 'Windows':
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        except:
            is_admin = False
        if not is_admin:
            # Relaunch the script with admin rights
            script = os.path.abspath(sys.argv[0])
            params = ' '.join(['"' + arg + '"' for arg in sys.argv[1:]])
            result = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, f'"{script}" {params}', None, 1)
            if result <= 32:
                # The user declined the UAC prompt or an error occurred
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Critical)
                msg_box.setWindowTitle("Admin Privileges Required")
                msg_box.setText("This application requires administrator privileges to run.")
                msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
                msg_box.raise_()
                msg_box.activateWindow()
                msg_box.exec()
                sys.exit()
            sys.exit()
    main = MainApp()
    main.show()
    sys.exit(app.exec())
    #com.an.Datadash