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
from file_receiver_python import ReceiveAppP
from file_receiver_android import ReceiveAppPJava

SENDER_JSON = 53000
RECEIVER_JSON = 54000

class FileReceiver(QThread):
    show_receive_app_p_signal = pyqtSignal()  # Signal to show the ReceiveAppP window
    show_receive_app_p_signal_java = pyqtSignal()  # Signal to show the ReceiveAppP window for Java devices

    def __init__(self):
        super().__init__()
        self.encrypted_files = []
        self.broadcasting = True
        self.metadata = None
        self.destination_folder = None
        self.client_ip = None
        self.server_socket = None
        self.client_socket = None
        self.receiver_worker = None

    def run(self):
        # Clear all connections on the about to be used ports 
        try:
            self.server_socket.shutdown(socket.SHUT_RDWR)
            self.server_socket.close()
        except AttributeError:
            pass

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(('0.0.0.0', RECEIVER_JSON))
        self.server_socket.listen(5)  # Listen for multiple connections

        while True:
            self.client_socket, addr = self.server_socket.accept()
            self.store_client_ip()
            self.handle_device_type()
            self.client_socket.close()  # Close the connection after receiving files

    def store_client_ip(self):
        """Extract and store the IP address of the connected client."""
        self.client_ip = self.client_socket.getpeername()[0]
        logger.debug(f"Client IP address stored: {self.client_ip}")
        return self.client_ip

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
        # print logger info of client_socket ip address
        logger.debug(f"Connected to {self.client_socket.getpeername()}")

        # Receive and process the device information from the sender
        device_json_size = struct.unpack('<Q', self.client_socket.recv(8))[0]
        device_json = self.client_socket.recv(device_json_size).decode()
        self.device_info = json.loads(device_json)
        sender_device_type = self.device_info.get("device_type", "unknown")
        if sender_device_type == "python":
            logger.debug("Connected to a Python device.")
            self.show_receive_app_p_signal.emit()
            sleep(1)  # Wait for the signal to be processed
            self.cleanup_sockets() # Clean up before proceeding
        elif sender_device_type == "java":
            logger.debug("Connected to a Java device, but this feature is not implemented yet.")
            self.show_receive_app_p_signal_java.emit()
            sleep(1)
            self.cleanup_sockets()
        else:
            logger.debug("Unknown device type received.")
    
    def cleanup_sockets(self):
        if self.client_socket:
            self.client_socket.close()



class ReceiveApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Receive File')
        self.setGeometry(100, 100, 300, 200)
        self.center_window()

        layout = QVBoxLayout()

        self.label = QLabel("Waiting for Connection...", self)
        layout.addWidget(self.label)

        self.setLayout(layout)

        self.file_receiver = FileReceiver()
        self.file_receiver.show_receive_app_p_signal.connect(self.show_receive_app_p)  # Connect the signal to the slot
        self.file_receiver.show_receive_app_p_signal_java.connect(self.show_receive_app_p_java)
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

    def show_receive_app_p(self):
        client_ip = self.file_receiver.client_ip
        """Slot to show the ReceiveAppP window on the main thread."""
        self.hide()
        self.receive_app_p = ReceiveAppP(client_ip)
        self.receive_app_p.show()

    def show_receive_app_p_java(self):
        client_ip = self.file_receiver.client_ip
        """Slot to show the ReceiveAppP window on the main thread."""
        self.hide()
        self.receive_app_p_java = ReceiveAppPJava(client_ip)
        self.receive_app_p_java.show()

    def center_window(self):
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        window_width, window_height = 800, 600
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2
        self.setGeometry(x, y, window_width, window_height)


if __name__ == '__main__':
    import sys
    app = QApplication([])
    receive_app = ReceiveApp()
    receive_app.show()
    app.exec()