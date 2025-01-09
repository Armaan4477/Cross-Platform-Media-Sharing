import sys
import json
import platform
import socket
import struct
import math
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QMessageBox, QListWidget, QListWidgetItem, QFrame
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QPointF, QTimer, QSize
from PyQt6.QtGui import QScreen, QColor, QLinearGradient, QPainter, QPen, QFont, QIcon, QKeySequence, QKeyEvent
from loges import logger
from constant import ConfigManager  # Updated import
from portsss import BROADCAST_PORT, LISTEN_PORT, RECEIVER_JSON
from file_sender import SendApp
from file_sender_java import SendAppJava
from file_sender_swift import SendAppSwift
import os
import time

BROADCAST_ADDRESS="255.255.255.255"

class CircularDeviceButton(QWidget):
    def __init__(self, device_name, device_ip, parent=None):
        super().__init__(parent)
        self.device_name = device_name
        self.device_ip = device_ip

        # Create a QPushButton for the device (initials or first letter)
        self.button = QPushButton(device_name[0], self)
        self.button.setFixedSize(50, 50)  # Button size
        self.button.setStyleSheet("""
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
                font-size: 20px;
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

        # Create a QLabel for the full device name below the button
        self.device_label = QLabel(device_name, self)
        self.device_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 14px;
                font-weight: normal;
            }
        """)
        self.device_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Set up the layout: button above and label below
        layout = QVBoxLayout(self)
        layout.addWidget(self.button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.device_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Reduce the spacing and margins between the button and label
        layout.setSpacing(2)  # Set small spacing between button and label
        layout.setContentsMargins(0, 0, 0, 0)  # Remove margins around the layout
        self.setLayout(layout)
        #com.an.Datadash

class BroadcastWorker(QThread):
    device_detected = pyqtSignal(dict)
    device_connected = pyqtSignal(str, str, dict)
    device_connected_java = pyqtSignal(str, str, dict)
    device_connected_swift = pyqtSignal(str, str, dict)

    def __init__(self):
        super().__init__()
        self.socket = None
        self.client_socket = None
        self.receiver_data = None
        self.config_manager = ConfigManager()
        self.config_manager.start()
        self.running = True

    def run(self):
        logger.info("Starting receiver discovery process")
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as s:
                # Configure socket
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.settimeout(2.0)
                s.bind(('', LISTEN_PORT))

                start_time = time.time()
                timeout_duration = 8.0
                broadcast_address = BROADCAST_ADDRESS
                message = "DISCOVER".encode('utf-8')

                logger.info(f"Sending DISCOVER message to {broadcast_address}:{BROADCAST_PORT}")
                s.sendto(message, (broadcast_address, BROADCAST_PORT))

                while (time.time() - start_time) < timeout_duration and self.running:
                    try:
                        data, addr = s.recvfrom(1024)
                        message = data.decode()
                        logger.info(f"Received response from {addr[0]}: {message}")

                        if message.startswith('RECEIVER:'):
                            device_name = message.split(':')[1]
                            device_info = {
                                'ip': addr[0],
                                'name': device_name
                            }
                            logger.info(f"Found valid device: {device_info}")
                            self.device_detected.emit(device_info)

                    except socket.timeout:
                        logger.debug("Socket timeout while waiting for response")
                        continue
                    except Exception as e:
                        logger.error(f"Error processing response: {str(e)}")
                        continue

        except Exception as e:
            logger.error(f"Critical broadcast error: {str(e)}")
        finally:
            logger.info("Discovery process completed")

    def connect_to_device(self, device_ip, device_name):
        logger.info(f"Initiating connection to device {device_name} ({device_ip})")
        try:
            if self.client_socket:
                logger.debug("Closing existing socket connection")
                self.client_socket.shutdown(socket.SHUT_RDWR)
                self.client_socket.close()
            
            logger.debug("Creating new TCP socket")
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            logger.info(f"Attempting to connect to {device_ip}:{RECEIVER_JSON}")
            self.client_socket.connect((device_ip, RECEIVER_JSON))

            device_data = {
                'device_type': 'python',
                'os': platform.system()
            }
            logger.debug(f"Sending device data: {device_data}")
            device_data_json = json.dumps(device_data)
            self.client_socket.send(struct.pack('<Q', len(device_data_json)))
            self.client_socket.send(device_data_json.encode())

            logger.debug("Waiting for receiver data")
            receiver_json_size = struct.unpack('<Q', self.client_socket.recv(8))[0]
            receiver_json = self.client_socket.recv(receiver_json_size).decode()
            self.receiver_data = json.loads(receiver_json)
            logger.info(f"Received device data: {self.receiver_data}")

            device_type = self.receiver_data.get('device_type', 'unknown')
            logger.info(f"Detected device type: {device_type}")

            if device_type == 'python':
                logger.info("Connecting to Python device")
                self.device_connected.emit(device_ip, device_name, self.receiver_data)
                self.client_socket.close()
            elif device_type == 'java':
                logger.info("Connecting to Java device")
                self.device_connected_java.emit(device_ip, device_name, self.receiver_data)
            elif device_type == 'swift':
                logger.info("Connecting to Swift device")
                self.device_connected_swift.emit(device_ip, device_name, self.receiver_data)
            else:
                logger.error(f"Unsupported device type: {device_type}")
                raise ValueError("Unsupported device type")

        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            QMessageBox.critical(None, "Connection Error", f"Failed to connect: {str(e)}")
        finally:
            if self.client_socket:
                logger.debug("Closing socket connection")
                self.client_socket.close()

    def closeEvent(self, event):
        # Ensure socket is forcefully closed
        if self.worker.client_socket:
            try:
                self.worker.client_socket.shutdown(socket.SHUT_RDWR)
                self.worker.client_socket.close()
                print("Socket closed on window switch or close.")
            except Exception as e:
                logger.error(f"Error closing socket: {str(e)}")
        event.accept()  # Accept the window close event

    def stop(self):
        self.running = False
        if self.client_socket:
            try:
                self.client_socket.shutdown(socket.SHUT_RDWR)
                self.client_socket.close()
            except Exception as e:
                logger.error(f"Error stopping socket: {str(e)}")
                #com.an.Datadash


class Broadcast(QWidget):
    
   
    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.config_manager.config_updated.connect(self.on_config_updated)
        self.config_manager.log_message.connect(logger.info)
        self.config_manager.start()
        self.setWindowTitle('Device Discovery')
        self.setFixedSize(853, 480)  # Updated to 1280x720 (16:9 ratio)
        self.center_window()

        self.devices = []
        self.broadcast_worker = BroadcastWorker()
        self.broadcast_worker.device_detected.connect(self.add_device)
        self.broadcast_worker.device_connected.connect(self.show_send_app)
        self.broadcast_worker.device_connected_java.connect(self.show_send_app_java)
        self.broadcast_worker.device_connected_swift.connect(self.show_send_app_swift)

        self.animation_offset = 0
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_timer.start(50)  # Update every 50ms
        self.initUI()
        self.discover_devices()
        self.send_app = None
        self.send_app_java = None
        self.send_app_swift = None
        self.main_window = None

    def initUI(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        #com.an.Datadash

        # Header
        header = QFrame()
        header.setFixedHeight(70)
        header.setStyleSheet("background-color: #333; padding: 0px;")
        header_layout = QHBoxLayout(header)

        title_label = QLabel("Device Discovery")
        title_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        title_label.setStyleSheet("color: white;")
        header_layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout.addWidget(header)

        # Main content area
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        # Circular device display
        self.device_area = QWidget()
        self.device_area.setFixedSize(600, 600)  # Increased size for larger window
        content_layout.addWidget(self.device_area, alignment=Qt.AlignmentFlag.AlignCenter)

        # Refresh button
        self.refresh_button = QPushButton('Refresh')
        self.style_button(self.refresh_button)
        self.refresh_button.clicked.connect(self.discover_devices)
        content_layout.addWidget(self.refresh_button, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout.addWidget(content)
        #com.an.Datadash
        self.setLayout(main_layout)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.openMainWindow()

    def openMainWindow(self):
        from main import MainApp
        self.main_window = MainApp()
        self.main_window.show()
        self.close()
        
    def style_button(self, button):
        button.setFixedSize(180, 60)  # Increased size for better visibility
        button.setFont(QFont("Arial", 18))
        button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(47, 54, 66, 255),
                    stop: 1 rgba(75, 85, 98, 255)
                );
                color: white;
                border-radius: 30px;
                border: 1px solid rgba(0, 0, 0, 0.5);
                padding: 8px;
                font-weight: bold;
                font-size: 18px;
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

    def center_window(self):
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        window_width, window_height = 853, 480
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2
        self.setGeometry(x, y, window_width, window_height)

    def update_animation(self):
        self.animation_offset += 1
        if self.animation_offset > 60:  # Adjusted for larger animation
            self.animation_offset = 0
        self.update()

    def discover_devices(self):
        self.devices.clear()
        for child in self.device_area.children():
            if isinstance(child, CircularDeviceButton):
                child.deleteLater()
        self.broadcast_worker.start()

    def add_device(self, device_info):
        self.devices.append(device_info)
        self.update_devices()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw background gradient
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor('#b0b0b0'))
        gradient.setColorAt(1, QColor('#505050'))
        painter.fillRect(self.rect(), gradient)

        # Draw animated circular rings with reduced size for smaller window
        painter.setPen(QPen(Qt.GlobalColor.white, 3))  # Line width remains the same
        center = QPointF(self.width() / 2, self.height() / 2)
        self.center = center
        for i in range(4):
            radius = 97 - i * 26  # Reduced size for the circles
            painter.drawEllipse(center, radius + self.animation_offset, radius + self.animation_offset)

    def update_devices(self):
        # Remove previous device buttons
        for child in self.device_area.children():
            if isinstance(child, CircularDeviceButton):
                child.deleteLater()

        # Position the device buttons on the reduced circle size
        radius = 105  # Smaller circle for the device buttons
        center_x, center_y = 296, 160  # Adjusted center for the smaller window

        for i, device in enumerate(self.devices):
            angle = i * (2 * math.pi / len(self.devices))
            x = center_x + radius * math.cos(angle) - 32  # Adjusted for smaller window
            y = center_y + radius * math.sin(angle) - 20  # Adjusted for smaller window
            button_with_label = CircularDeviceButton(device['name'], device['ip'], self.device_area)
            button_with_label.move(int(x), int(y))
            button_with_label.button.clicked.connect(lambda checked, d=device: self.connect_to_device(d))
            button_with_label.show()

    def connect_to_device(self, device):
        confirm_dialog = QMessageBox(self)
        confirm_dialog.setWindowTitle("Confirm Connection")
        confirm_dialog.setText(f"Connect to {device['name']}?")
        confirm_dialog.setIcon(QMessageBox.Icon.Question)
        #com.an.Datadash

        # Add buttons
        yes_button = confirm_dialog.addButton("Yes", QMessageBox.ButtonRole.YesRole)
        no_button = confirm_dialog.addButton("No", QMessageBox.ButtonRole.NoRole)

        # Apply consistent styling
        confirm_dialog.setStyleSheet("""
            QMessageBox {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #b0b0b0,
                    stop: 1 #505050
                );
                color: #FFFFFF;
                font-size: 18px;
            }
            QLabel {
                background-color: transparent;
                font-size: 18px;
            }
            QPushButton {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(47, 54, 66, 255),
                    stop: 1 rgba(75, 85, 98, 255)
                );
                color: white;
                border-radius: 15px;
                border: 1px solid rgba(0, 0, 0, 0.5);
                padding: 8px;
                font-size: 18px;
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

        confirm_dialog.exec()

        if confirm_dialog.clickedButton() == yes_button:
            self.broadcast_worker.connect_to_device(device['ip'], device['name'])

    def show_send_app(self, device_ip, device_name, receiver_data):
        self.hide()
        self.send_app = SendApp(device_ip, device_name, receiver_data)
        self.send_app.show()

    def show_send_app_java(self, device_ip, device_name, receiver_data):
        self.hide()
        self.send_app_java = SendAppJava(device_ip, device_name, receiver_data)
        self.send_app_java.show()
        #com.an.Datadash

    def show_send_app_swift(self, device_ip, device_name, receiver_data):
        config = self.config_manager.get_config()
        if config["encryption"] and config["show_warning"]:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Input Error")
                msg_box.setText("You have encryption Enabled, unfortunately IOS/IpadOS tranfer doesn't support that yet. Clicking ok will bypass your encryption settings for this file transfer.")
                msg_box.setIcon(QMessageBox.Icon.Critical)
                msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)

                # Apply custom style with gradient background
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
                    background-color: transparent; /* Make the label background transparent */
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
                msg_box.exec() 
        
        self.hide()
        self.send_app_swift = SendAppSwift(device_ip, device_name, receiver_data)
        self.send_app_swift.show()
        #com.an.Datadash

    def closeEvent(self, event):
        # Ensure socket is forcefully closed
        try:
            if self.worker.client_socket:
                try:
                    self.worker.client_socket.shutdown(socket.SHUT_RDWR)
                    self.worker.client_socket.close()
                    print("Socket closed on window switch or close.")
                except Exception as e:
                    print(f"Error closing socket: {str(e)}")
        except Exception as e:
            pass
        finally:
            self.broadcast_worker.stop()
            event.accept()  # Accept the window close event
    
    def stop(self):
        # Method to manually stop the socket
        if self.client_socket:
            try:
                self.client_socket.shutdown(socket.SHUT_RDWR)
                self.client_socket.close()
                print("Socket closed manually.")
            except Exception as e:
                print(f"Error stopping socket: {str(e)}")

    def on_config_updated(self, config):
        """Handler for config updates"""
        self.current_config = config

    def cleanup(self):
        # Stop broadcast worker thread
        if self.broadcast_worker:
            self.broadcast_worker.stop()
            self.broadcast_worker.quit()
            self.broadcast_worker.wait()

        # Close all child windows
        for window in [self.send_app, self.send_app_java, self.send_app_swift, self.main_window]:
            if window:
                window.close()

    def closeEvent(self, event):
        logger.info("Shutting down Broadcast window")
        self.cleanup()
        QApplication.quit()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    broadcast_app = Broadcast()
    broadcast_app.show()
    sys.exit(app.exec()) 
    #com.an.Datadash