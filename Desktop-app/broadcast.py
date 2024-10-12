import sys
import json
import platform
import socket
import struct
import time
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QPoint, QTimer, QSize
from PyQt6.QtGui import QScreen, QColor, QPainter, QPen, QBrush, QFont
from constant import BROADCAST_ADDRESS, BROADCAST_PORT, LISTEN_PORT, logger
from file_sender import SendApp
from file_sender_java import SendAppJava
import subprocess
from time import sleep

SENDER_JSON = 53000
RECEIVER_JSON = 54000

class BroadcastWorker(QThread):
    device_detected = pyqtSignal(dict)
    device_connected = pyqtSignal(str, str, dict)
    device_connected_java = pyqtSignal(str, str, dict)
    discovery_complete = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.socket = None
        self.broadcast_worker = None
        self.client_socket = None
        self.receiver_data = None

    def run(self):
        receivers = []
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('', LISTEN_PORT))

        self.socket.sendto(b'DISCOVER', (BROADCAST_ADDRESS, BROADCAST_PORT))

        self.socket.settimeout(2)
        try:
            while True:
                message, address = self.socket.recvfrom(1024)
                message = message.decode()
                if message.startswith('RECEIVER:'):
                    device_name = message.split(':')[1]
                    receivers.append({'ip': address[0], 'name': device_name})
                    self.device_detected.emit({'ip': address[0], 'name': device_name})
        except socket.timeout:
            pass
        finally:
            self.close_socket()

    def close_socket(self):
        if self.socket:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
            self.socket.close()
            self.socket = None

    def stop(self):
        self.close_socket()
        self.quit()
        self.wait()

    def discover_receivers(self):
        logger.info("Starting device discovery")
        receivers = []
        max_attempts = 3
        attempt = 0

        while attempt < max_attempts:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.bind(('', LISTEN_PORT))
                    logger.info(f"Bound to port {LISTEN_PORT}")

                    s.sendto(b'DISCOVER', (BROADCAST_ADDRESS, BROADCAST_PORT))
                    logger.info(f"Sent discovery message to {BROADCAST_ADDRESS}:{BROADCAST_PORT}")

                    s.settimeout(2)
                    start_time = time.time()
                    while time.time() - start_time < 5:  # Listen for responses for 5 seconds
                        try:
                            message, address = s.recvfrom(1024)
                            message = message.decode()
                            logger.info(f"Received message: {message} from {address}")
                            if message.startswith('RECEIVER:'):
                                device_name = message.split(':')[1]
                                receiver = {'ip': address[0], 'name': device_name}
                                if receiver not in receivers:
                                    receivers.append(receiver)
                                    logger.info(f"Added device: {device_name} ({address[0]})")
                        except socket.timeout:
                            logger.info("Socket timeout, continuing to listen")
                            continue  # Continue listening if a timeout occurs
                
                if receivers:
                    logger.info(f"Discovery complete. Found {len(receivers)} device(s)")
                    break  # Exit the loop if we found any receivers
            except Exception as e:
                logger.error(f"Error during discovery attempt {attempt + 1}: {str(e)}")
            
            attempt += 1
            if attempt < max_attempts:
                logger.info(f"Retrying discovery (attempt {attempt + 1})")
        
        if not receivers:
            logger.warning("No devices found after all attempts")
        
        self.discovery_complete.emit(bool(receivers))
        return receivers

    def connect_to_device(self, device_ip, device_name):
        confirm = QMessageBox.question(None, 'Confirm Connection', f"Connect to {device_name}?", 
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            logger.info(f"Connecting to {device_name} at {device_ip}")
            device_type = self.initialize_connection(device_ip)

            if device_type == 'python':
                logger.info(f"Connected with Python device {device_name}")
                self.cleanup_sockets()
                sleep(1)
                self.device_connected.emit(device_ip, device_name, self.receiver_data)
            elif device_type == 'java':
                logger.info(f"Connected with Java device {device_name}")
                self.cleanup_sockets()
                sleep(1)
                self.device_connected_java.emit(device_ip, device_name, self.receiver_data)

    def initialize_connection(self, ip_address):
        logger.debug("Initializing connection")
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_socket.bind(('', SENDER_JSON))
            logger.debug("Binded to port %d", SENDER_JSON)
            self.client_socket.connect((ip_address, RECEIVER_JSON))
            logger.debug("Connected to %s", ip_address)
        except ConnectionRefusedError:
            QMessageBox.critical(None, "Connection Error", "Failed to connect to the specified IP address.")
            return None

        device_data = {
            'device_type': 'python',
            'os': platform.system()
        }
        device_data_json = json.dumps(device_data)
        self.client_socket.send(struct.pack('<Q', len(device_data_json)))
        self.client_socket.send(device_data_json.encode())

        receiver_json_size = struct.unpack('<Q', self.client_socket.recv(8))[0]
        logger.debug("Receiver JSON size: %d", receiver_json_size)
        receiver_json = self.client_socket.recv(receiver_json_size).decode()
        self.receiver_data = json.loads(receiver_json)
        logger.debug("Receiver data: %s", self.receiver_data)

        device_type = self.receiver_data.get('device_type', 'unknown')
        if device_type in ['python', 'java', 'swift']:
            logger.debug(f"Receiver is a {device_type} device")
            return device_type
        else:
            QMessageBox.critical(None, "Device Error", "The receiver device is not compatible.")
            self.cleanup_sockets()
            return None

    def cleanup_sockets(self):
        if self.client_socket:
            self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
            self.client_socket.close()
        if self.isRunning():
            self.stop()

class CircularWidget(QWidget):
    clicked = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.setMinimumSize(600, 600)
        self.devices = []
        self.animation_offset = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(50)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center = QPoint(self.width() // 2, self.height() // 2)
        for i in range(4, 0, -1):
            radius = i * 70 + self.animation_offset
            painter.setPen(QPen(QColor("white"), 2))
            painter.drawEllipse(center, radius, radius)

        painter.setBrush(QBrush(QColor("white")))
        painter.drawEllipse(center, 20, 20)

        if self.devices:
            angle_step = 360 / len(self.devices)
            for i, device in enumerate(self.devices):
                angle = i * angle_step
                x = center.x() + int(250 * -1 * (angle / 360) * 2 * 3.14159)
                y = center.y() + int(250 * -1 * (angle / 360) * 2 * 3.14159)
                painter.setBrush(QBrush(QColor("white")))
                painter.drawEllipse(QPoint(x, y), 30, 30)
                painter.setPen(QPen(QColor("#4B0082")))
                painter.setFont(QFont("Arial", 12))
                painter.drawText(QPoint(x-15, y+5), device['name'][:2])

    def update_animation(self):
        self.animation_offset += 1
        if self.animation_offset > 70:
            self.animation_offset = 0
        self.update()

    def mousePressEvent(self, event):
        center = QPoint(self.width() // 2, self.height() // 2)
        for device in self.devices:
            angle = self.devices.index(device) * (360 / len(self.devices))
            x = center.x() + int(250 * -1 * (angle / 360) * 2 * 3.14159)
            y = center.y() + int(250 * -1 * (angle / 360) * 2 * 3.14159)
            if (QPoint(x, y) - event.position().toPoint()).manhattanLength() <= 30:
                self.clicked.emit(device['ip'], device['name'])

    def set_devices(self, devices):
        self.devices = devices
        self.update()

class Broadcast(QWidget):
    device_connected = pyqtSignal(str, str, dict)
    device_connected_java = pyqtSignal(str, str, dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Device Discovery')
        self.setGeometry(100, 100, 1280, 720)  # 16:9 ratio
        self.center_window()
        self.setStyleSheet(f"background-color: #4B0082; color: white;")

        layout = QVBoxLayout()

        self.title_label = QLabel("Searching for devices...")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(self.title_label)

        self.circular_widget = CircularWidget()
        self.circular_widget.clicked.connect(self.on_device_clicked)
        layout.addWidget(self.circular_widget)

        self.refresh_button = QPushButton('Refresh')
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #4B0082;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #E6E6E6;
            }
        """)
        self.refresh_button.clicked.connect(self.discover_devices)
        layout.addWidget(self.refresh_button)

        self.setLayout(layout)

        self.broadcast_worker = BroadcastWorker()
        self.broadcast_worker.device_detected.connect(self.add_device_to_list)
        self.broadcast_worker.device_connected.connect(self.show_send_app)
        self.broadcast_worker.device_connected_java.connect(self.show_send_app_java)
        self.broadcast_worker.discovery_complete.connect(self.on_discovery_complete)
        self.discover_devices()

        self.client_socket = None

    def center_window(self):
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        window_width, window_height = 1280, 720
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2
        self.setGeometry(x, y, window_width, window_height)

    def discover_devices(self):
        self.title_label.setText("Searching for devices...")
        self.circular_widget.set_devices([])
        self.refresh_button.setEnabled(False)
        QApplication.processEvents()  # Force UI update
        
        # Run discovery in a separate thread
        self.discovery_thread = QThread()
        self.broadcast_worker.moveToThread(self.discovery_thread)
        self.discovery_thread.started.connect(self.broadcast_worker.discover_receivers)
        self.broadcast_worker.discovery_complete.connect(self.discovery_thread.quit)
        self.discovery_thread.finished.connect(self.on_discovery_finished)
        self.discovery_thread.start()

    def on_discovery_complete(self, devices_found):
        if devices_found:
            self.title_label.setText("Tap avatar to connect")
        else:
            self.title_label.setText("No devices found. Try refreshing.")

    def on_discovery_finished(self):
        self.refresh_button.setEnabled(True)
        receivers = self.broadcast_worker.discover_receivers()
        for receiver in receivers:
            self.add_device_to_list(receiver)

    def add_device_to_list(self, device_info):
        devices = self.circular_widget.devices + [device_info]
        self.circular_widget.set_devices(devices)

    def on_device_clicked(self, device_ip, device_name):
        self.broadcast_worker.connect_to_device(device_ip, device_name)

    def show_send_app(self, device_ip, device_name, receiver_data):
        self.hide()
        self.send_app = SendApp(device_ip, device_name, receiver_data)
        self.send_app.show()
    
    def show_send_app_java(self, device_ip, device_name,   receiver_data):
        self.hide()
        self.send_app_java = SendAppJava(device_ip, device_name, receiver_data)
        self.send_app_java.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    broadcast_app = Broadcast()
    broadcast_app.show()
    sys.exit(app.exec())