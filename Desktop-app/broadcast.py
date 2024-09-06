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
import subprocess
from time import sleep

SENDER_JSON = 53000
RECEIVER_JSON = 54000

class BroadcastWorker(QThread):
    device_detected = pyqtSignal(dict)
    device_connected = pyqtSignal(str, str, dict)  # Signal to emit when a device is connected

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
            self.close_socket()  # Ensure the socket is closed when done

    def close_socket(self):
        if self.socket:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))  # Force immediate close
            self.socket.close()
            self.socket = None

    def stop(self):
        self.close_socket()  # Ensure the socket is closed when stopping the thread
        self.quit()
        self.wait()

    def discover_receivers(self):
        logger.info("Discovering receivers")
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

        confirm = QMessageBox.question(None, 'Confirm Connection', f"Connect to {device_name}?", 
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            logger.info(f"Connecting to {device_name} at {device_ip}")
            device_type = self.initialize_connection(device_ip)

            if device_type == 'python':
                logger.info(f"Connected with Python device {device_name}")
                self.cleanup_sockets()  # Clean up before proceeding
                sleep(1)  # Wait for the receiver to close the socket
                # Emit signal with device information when a connection is established
                self.device_connected.emit(device_ip, device_name, self.receiver_data)

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

        # Send and receive a JSON file containing device type information
        device_data = {
            'device_type': 'python',
            'os': platform.system()
        }
        device_data_json = json.dumps(device_data)
        self.client_socket.send(struct.pack('<Q', len(device_data_json)))
        self.client_socket.send(device_data_json.encode())

        # Receive the JSON file from the receiver
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
            self.cleanup_sockets()  # Clean up if the device is not compatible
            return None


    def cleanup_sockets(self):
        if self.client_socket:
            self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))  # Force immediate close
            self.client_socket.close()
        if self.isRunning():
            self.stop()

class Broadcast(QWidget):
    device_connected = pyqtSignal(str, str, dict)  # Signal to indicate device connection

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Device Discovery')
        self.setGeometry(100, 100, 400, 300)
        self.center_window()

        layout = QVBoxLayout()

        self.device_list = QListWidget(self)
        self.device_list.itemClicked.connect(self.connect_to_device)
        layout.addWidget(self.device_list)

        self.refresh_button = QPushButton('Refresh', self)
        self.refresh_button.clicked.connect(self.discover_devices)
        layout.addWidget(self.refresh_button)

        self.setLayout(layout)

        # Initialize BroadcastWorker instance
        self.broadcast_worker = BroadcastWorker()
        self.broadcast_worker.device_detected.connect(self.add_device_to_list)
        self.broadcast_worker.device_connected.connect(self.show_send_app)  # Connect the worker's signal to slot
        self.discover_devices()

        self.client_socket = None

    def center_window(self):
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        window_width, window_height = 400, 300
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2
        self.setGeometry(x, y, window_width, window_height)

    def discover_devices(self):
        self.device_list.clear()
        receivers = self.broadcast_worker.discover_receivers()  # Correctly call the discover_receivers method from BroadcastWorker instance
        for receiver in receivers:
            item = QListWidgetItem(receiver['name'])
            item.setData(256, receiver['name'])  # Store device name
            item.setData(257, receiver['ip'])  # Store device IP
            self.device_list.addItem(item)

    def connect_to_device(self, item):
        # Ensure you connect through the correct method
        self.broadcast_worker.connect_to_device(item)

    def add_device_to_list(self, device_info):
        # Add the detected device to the list
        item = QListWidgetItem(device_info['name'])
        item.setData(256, device_info['name'])  # Store device name
        item.setData(257, device_info['ip'])  # Store device IP
        self.device_list.addItem(item)

    def show_send_app(self, device_ip, device_name, receiver_data):
        self.hide()
        self.send_app = SendApp(device_ip, device_name, receiver_data)  # Pass parameters to SendApp
        self.send_app.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    broadcast_app = Broadcast()
    broadcast_app.show()
    sys.exit(app.exec())