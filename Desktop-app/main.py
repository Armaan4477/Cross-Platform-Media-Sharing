from constant import ConfigManager
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QApplication,
                             QLabel, QFrame, QGraphicsDropShadowEffect, QMessageBox)
from PyQt6.QtGui import QScreen, QFont, QColor, QIcon, QMovie
from PyQt6.QtCore import Qt, QTimer, QSize, QThread, pyqtSignal
import sys
import os
from file_receiver import ReceiveApp
from broadcast import Broadcast
from preferences import PreferencesApp
import platform
import requests
import ctypes
from loges import logger
import subprocess
import json

class VersionCheck(QThread):
    update_available = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.uga_version = None
        self.config_manager = ConfigManager()

    def run(self):
        self.currentversion()
        self.get_platform_link()
        fetched_version = self.fetch_platform_value()
        if fetched_version and self.compare_versions(fetched_version, self.uga_version) > 0:
            self.update_available.emit()

    def fetch_platform_value(self):
        url = self.get_platform_link()
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
        
        while len(v1_parts) < 4:
            v1_parts.append(0)
        while len(v2_parts) < 4:
            v2_parts.append(0)
        
        return (v1_parts > v2_parts) - (v1_parts < v2_parts)

    def currentversion(self):
        self.uga_version = self.config_manager.get_config()["version"]
        logger.info(f"Current App version: {self.uga_version}")

    def get_platform_link(self):
        config = self.config_manager.get_config()
        channel = config["update_channel"]
        logger.info(f"Checking for updates in channel: {channel}")
        if platform.system() == 'Windows':
                platform_name = 'windows'
        elif platform.system() == 'Linux':
                platform_name = 'linux'
        elif platform.system() == 'Darwin':
                platform_name = 'macos'
        else:
                logger.error("Unsupported OS!")
                return None

        # for testing use the following line and comment the above lines, auga=older version, buga=newer version and cuga=latest version
        # platform_name = 'auga'
        # platform_name = 'buga'
        # platform_name = 'cuga'
            
        if channel == "stable":
            url = f"https://datadashshare.vercel.app/api/platformNumber?platform=python_{platform_name}"
            
        elif channel == "beta":
            url = f"https://datadashshare.vercel.app/api/platformNumberbeta?platform=python_{platform_name}"
        return url

class NetworkCheck(QThread):
    def __init__(self):
        super().__init__()

    def run(self):
        if platform.system() == 'Windows':
            self.check_network_type_windows()
            logger.info("Network check completed")

    def check_network_type_windows(self):
        try:
            cmd = '''
            $connections = @()
            Get-NetConnectionProfile | ForEach-Object {
                $connections += [PSCustomObject]@{
                    Name = (Get-NetAdapter -InterfaceIndex $_.InterfaceIndex).Name
                    NetworkCategory = $_.NetworkCategory.ToString()
                    Status = (Get-NetAdapter -InterfaceIndex $_.InterfaceIndex).Status
                }
            }
            $activeConnections = $connections | Where-Object { $_.Status -eq 'Up' }
            if ($activeConnections) {
                $activeConnections | ConvertTo-Json
            }
            '''
            
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

            result = subprocess.run(['powershell', '-ExecutionPolicy', 'Bypass', '-Command', cmd], 
                                 capture_output=True, 
                                 text=True,
                                 startupinfo=startupinfo)
            
            if result.returncode == 0 and result.stdout.strip():
                try:
                    network_data = json.loads(result.stdout)
                    if not isinstance(network_data, list):
                        network_data = [network_data]
                    
                    for network in network_data:
                        logger.info(f"Network interface: {network.get('Name')} - Category: {network.get('NetworkCategory')}")
                        if network.get('NetworkCategory', '').lower() == 'public':
                            logger.warning(f"Public network detected on interface: {network.get('Name')}")
                            return 'Public'
                    
                    logger.info("All network connections are Private")
                    return 'Private'
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON: {e}\nOutput: {result.stdout}")
                    return None
            else:
                logger.error(f"PowerShell command failed: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Error checking network type: {e}")
            return None

class MainApp(QWidget):
    def __init__(self, skip_version_check=False):
        super().__init__()
        self.config_manager = ConfigManager()
        self.config_manager.config_updated.connect(self.on_config_updated)
        self.config_manager.log_message.connect(logger.info)
        self.config_manager.config_ready.connect(self.on_config_ready)
        self.config_manager.start()
        self.skip_version_check = skip_version_check
        self.network_thread = NetworkCheck()
       # self.network_thread.start() #comment out after testing is over, lot of overhead on windows
        self.version_thread = None
        self.broadcast_app = None
        self.receive_app = None
        self.preferences_app = None

    def cleanup(self):
        if self.network_thread and self.network_thread.isRunning():
            self.network_thread.quit()
            self.network_thread.wait()

        if self.version_thread and self.version_thread.isRunning():
            self.version_thread.quit()
            self.version_thread.wait()

        if self.broadcast_app:
            self.broadcast_app.close()
        if self.receive_app:
            self.receive_app.close()
        if self.preferences_app:
            self.preferences_app.close()

        if hasattr(self, 'config_manager'):
            self.config_manager.quit()
            self.config_manager.wait()

    def closeEvent(self, event):
        self.cleanup()
        QApplication.quit()
        event.accept()

    def on_config_ready(self):
        self.initUI(self.skip_version_check)
        self.setFixedSize(853, 480)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def on_config_updated(self, config):
        self.current_config = config

    def initUI(self, skip_version_check=False):
        self.setWindowTitle('DataDash')
        self.setGeometry(100, 100, 853, 480)
        self.center_window()
        self.set_background()
        self.version_thread = VersionCheck()
        self.version_thread.update_available.connect(self.showmsgbox)
        if not skip_version_check:
            self.check_update()

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QFrame()
        header.setFixedHeight(70)
        header.setStyleSheet("background-color: #333; padding: 0px;")
        header_layout = QHBoxLayout(header)

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

        header_layout.addStretch()

        title_label = QLabel("DataDash: CrossPlatform Data Sharing")
        title_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        title_label.setStyleSheet("color: white;")
        header_layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)

        header_layout.addStretch()

        main_layout.addWidget(header)

        main_layout.addSpacing(20)

        gif_label = QLabel()
        gif_label.setStyleSheet("background-color: transparent;")
        movie = QMovie(os.path.join(os.path.dirname(__file__), "assets", "wifi.gif"))
        gif_label.setMovie(movie)
        movie.setScaledSize(QSize(500, 450))
        movie.start()
        main_layout.addWidget(gif_label, alignment=Qt.AlignmentFlag.AlignCenter)

        icon_path_send = os.path.join(os.path.dirname(__file__), "icons", "send.svg")
        icon_path_receive = os.path.join(os.path.dirname(__file__), "icons", "receive.svg")

        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        button_layout.setContentsMargins(30, 0, 30, 0)

        self.send_button = QPushButton('Send File')
        self.send_button.setIcon(QIcon(icon_path_send))
        self.send_button.setIconSize(QSize(24, 24))
        self.style_button(self.send_button)
        self.send_button.clicked.connect(self.sendFile)
        self.send_button.setToolTip("<b style='color: #FFA500; font-size: 14px;'>Send File</b><br><i style='font-size: 12px;'>Send a folder or multiple files to another device</i>")
        button_layout.addWidget(self.send_button)

        self.receive_button = QPushButton('Receive File')
        self.receive_button.setIcon(QIcon(icon_path_receive))
        self.receive_button.setIconSize(QSize(24, 24))
        self.style_button(self.receive_button)
        self.receive_button.clicked.connect(self.receiveFile)
        self.receive_button.setToolTip("<b style='color: #FFA500; font-size: 14px;'>Receive File</b><br><i style='font-size: 12px;'>Receive a folder or multiple files from another device</i>")
        button_layout.addWidget(self.receive_button)

        main_layout.addLayout(button_layout)
        main_layout.addSpacing(20)

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
        window_width, window_height = 853, 480
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2
        self.setGeometry(x, y, window_width, window_height)
        #com.an.Datadash
        dest = self.config_manager.get_config()["save_to_directory"]
        if not os.path.exists(dest):
            os.makedirs(dest)
            logger.info("Created folder to receive files")


    def sendFile(self):
        if self.config_manager.get_config()["show_warning"]:
            send_dialog = QMessageBox(self)
            send_dialog.setWindowTitle("Note")
            send_dialog.setText("""Before starting the transfer, please ensure both the sender and receiver devices are connected to the same network.
            """)
            send_dialog.setIcon(QMessageBox.Icon.Warning)

            proceed_button = send_dialog.addButton("Proceed", QMessageBox.ButtonRole.AcceptRole)
            cancel_button = send_dialog.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)

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
        if self.config_manager.get_config()["show_warning"]:
            receive_dialog = QMessageBox(self)
            receive_dialog.setWindowTitle("Note")
            receive_dialog.setText("""Before starting the transfer, please ensure both the sender and receiver devices are connected to the same network.
            """)
            receive_dialog.setIcon(QMessageBox.Icon.Warning)

            proceed_button = receive_dialog.addButton("Proceed", QMessageBox.ButtonRole.AcceptRole)
            cancel_button = receive_dialog.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)

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
        if self.config_manager.get_config()["check_update"]:
            logger.info("Checking for updates")
            self.version_thread = VersionCheck()
            self.version_thread.config_manager = self.config_manager
            self.version_thread.update_available.connect(self.showmsgbox)
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
    app.setQuitOnLastWindowClosed(True)
    main = MainApp()
    main.show()
    sys.exit(app.exec())
    #com.an.Datadash