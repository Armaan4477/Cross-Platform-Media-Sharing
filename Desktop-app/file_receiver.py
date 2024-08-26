import os
import platform
import socket
import struct
import threading
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QMessageBox, QWidget, QVBoxLayout, QLabel, QProgressBar, QApplication
)
from PyQt6.QtGui import QScreen
from constant import BROADCAST_ADDRESS, BROADCAST_PORT, LISTEN_PORT, get_config, logger
from crypt_handler import decrypt_file, Decryptor
from time import sleep
import json
from file_receiver_python import ReceiveWorkerPython

SENDER_JSON = 53000
RECEIVER_JSON = 54000
SENDER_DATA = 57000
RECEIVER_DATA = 58000

class FileReceiver(QThread):
    progress_update = pyqtSignal(int)
    decrypt_signal = pyqtSignal(list)
    password = None

    def __init__(self):
        super().__init__()
        self.encrypted_files = []
        self.broadcasting = True
        self.metadata = None
        self.destination_folder = None

    def run(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(('0.0.0.0', RECEIVER_JSON))

        self.server_socket.listen(5)  # Listen for multiple connections

        while True:
            self.client_socket, addr = self.server_socket.accept()
            self.handle_device_type()
            #client_socket.close()  # Close the connection after receiving files

        logger.debug("List of encrypted files: %s", self.encrypted_files)

    def handle_device_type(self):
        """Handles the device type negotiation and file receiving process."""
        # Send device information as JSON
        device_data = {
            "device_type": "python",
            "os": platform.system()
        }
        device_data_json = json.dumps(device_data)
        self.client_socket.send(struct.pack('<Q', len(device_data_json)))
        self.client_socket.send(device_data_json.encode())

        # Receive and process the device information from the sender
        device_json_size = struct.unpack('<Q', self.client_socket.recv(8))[0]
        device_json = self.client_socket.recv(device_json_size).decode()
        self.device_info = json.loads(device_json)
        sender_device_type = self.device_info.get("device_type", "unknown")
        if sender_device_type == "python":
            logger.debug("Connected to a Python device.")
            self.receive_files()
            self.client_socket.close()
        elif sender_device_type == "java":
            logger.debug("Connected to a Java device, but this feature is not implemented yet.")
            # You can handle Java-specific operations here if needed
        else:
            logger.debug("Unknown device type received.")

    def receive_files(self):
        worker = ReceiveWorkerPython()
        worker.initialize_connection()
        worker.receive_files()


class ReceiveApp(QWidget):
    progress_update = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Receive File')
        self.setGeometry(100, 100, 300, 200)
        self.center_window()

        layout = QVBoxLayout()

        self.label = QLabel("Waiting for file...", self)
        layout.addWidget(self.label)

        self.progress_bar = QProgressBar(self)
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)

        self.file_receiver = FileReceiver()
        self.file_receiver.start()

        self.broadcast_thread = threading.Thread(target=self.listenForBroadcast, daemon=True)
        self.broadcast_thread.start()

    def listenForBroadcast(self):
       with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
           s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
           s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
           s.bind(('', BROADCAST_PORT))

           while True:
               if self.file_receiver.broadcasting:
                   message, address = s.recvfrom(1024)
                   message = message.decode()
                   if message == 'DISCOVER':
                       response = f'RECEIVER:{get_config()["device_name"]}'
                       # Create a new socket to send the response on LISTEN_PORT
                       with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as response_socket:
                           response_socket.sendto(response.encode(), (address[0], LISTEN_PORT))
               sleep(1)  # Avoid busy-waiting

    def center_window(self):
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        window_width, window_height = 800, 600
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2
        self.setGeometry(x, y, window_width, window_height)
