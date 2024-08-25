import sys
import json
import platform
import socket
import struct
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QMessageBox, QPushButton
)
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QScreen
from constant import BROADCAST_ADDRESS, BROADCAST_PORT, LISTEN_PORT, logger
from file_sender import SendApp

RECEIVER_PORT = 12348

class BroadcastWorker(QThread):
    device_detected = pyqtSignal(dict)

    def run(self):
        receivers = []
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('', LISTEN_PORT))

            s.sendto(b'DISCOVER', (BROADCAST_ADDRESS, BROADCAST_PORT))

            s.settimeout(2)
            try:
                while True:
                    message, address = s.recvfrom(1024)
                    message = message.decode()
                    if message.startswith('RECEIVER:'):
                        device_name = message.split(':')[1]
                        receivers.append({'ip': address[0], 'name': device_name})
                        self.device_detected.emit({'ip': address[0], 'name': device_name})
            except socket.timeout:
                pass

class Broadcast(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Device Discovery')
        self.setGeometry(100, 100, 400, 300)
        self.center_window()

        layout = QVBoxLayout()

        self.device_list = QListWidget(self)
        self.device_list.itemClicked.connect(self.connect_to_device)
        layout.addWidget(self.device_list)

        self.refresh_button = QPushButton('Refresh')
        self.refresh_button.clicked.connect(self.discover_devices)
        layout.addWidget(self.refresh_button)

        self.setLayout(layout)
        self.discover_devices()

    def center_window(self):
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        window_width, window_height = 400, 300
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2
        self.setGeometry(x, y, window_width, window_height)

    def discover_devices(self):
        print("Discovering devices")
        self.device_list.clear()
        receivers = self.discover_receivers()
        for receiver in receivers:
            item = QListWidgetItem(receiver['name'])
            item.setData(256, receiver['name'])  # Store device name
            item.setData(257, receiver['ip'])  # Store device IP
            self.device_list.addItem(item)

    def discover_receivers(self):
        receivers = []
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('', LISTEN_PORT))

            s.sendto(b'DISCOVER', (BROADCAST_ADDRESS, BROADCAST_PORT))

            s.settimeout(2)
            try:
                while True:
                    message, address = s.recvfrom(1024)
                    message = message.decode()
                    if message.startswith('RECEIVER:'):
                        device_name = message.split(':')[1]
                        receivers.append({'ip': address[0], 'name': device_name})
            except socket.timeout:
                pass
        return receivers

    def connect_to_device(self, item):
        device_name = item.data(256)
        device_ip = item.data(257)

        confirm = QMessageBox.question(self, 'Confirm Connection', f"Connect to {device_name}?", 
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            logger.info(f"Connecting to {device_name} at {device_ip}")
            device_type = self.initialize_connection(device_ip)

            if device_type == 'python':
                logger.info(f"Connected with Python device {device_name}")
                #self.client_socket.close()
                self.hide()
                self.file_sender = SendApp(device_ip,device_name,self.receiver_data,self.client_socket)
                self.file_sender.show()
            elif device_type == 'java':
                logger.info(f"Connected with Java device {device_name}")

    def initialize_connection(self, ip_address):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_socket.connect((ip_address, RECEIVER_PORT))
        except ConnectionRefusedError:
            QMessageBox.critical(None, "Connection Error", "Failed to connect to the specified IP address.")
            return None

        # Send and receive a JSON file containing device type information
        device_data = {
            'device_type': 'python',
            'os': platform.system(),
            'ip': socket.gethostbyname(socket.gethostname())
        }
        device_data_json = json.dumps(device_data)
        self.client_socket.send(struct.pack('<Q', len(device_data_json)))
        self.client_socket.send(device_data_json.encode())

        # Receive the JSON file from the receiver
        receiver_json_size = struct.unpack('<Q', self.client_socket.recv(8))[0]
        receiver_json = self.client_socket.recv(receiver_json_size).decode()
        self.receiver_data = json.loads(receiver_json)
        logger.debug("Receiver data: %s", self.receiver_data)

        device_type = self.receiver_data.get('device_type', 'unknown')
        if device_type in ['python', 'java', 'swift']:
            logger.debug(f"Receiver is a {device_type} device")
            return device_type
        else:
            QMessageBox.critical(None, "Device Error", "The receiver device is not compatible.")
            self.client_socket.close()
            return None

if __name__ == '__main__':
    app = QApplication(sys.argv)
    broadcast_app = Broadcast()
    broadcast_app.show()
    sys.exit(app.exec())
