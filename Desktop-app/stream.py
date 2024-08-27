import sys
import json
import platform
import socket
import struct
import threading
from time import sleep
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QProgressBar
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QScreen
from file_receiver import CreateUIForReceiver
from constant import BROADCAST_PORT, LISTEN_PORT, get_config, logger
from crypt_handler import Decryptor

RECEIVER_PORT = 12348

class StreamSignal(QWidget):
    progress_update = pyqtSignal(int)
    decryptor_init = pyqtSignal(list)  # Changed to signal list for Decryptor

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

        # Start the broadcast listening in a separate thread
        self.broadcast_thread = threading.Thread(target=self.listenForBroadcast, daemon=True)
        self.broadcast_thread.start()

    def listenForBroadcast(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('', BROADCAST_PORT))

            while True:
                try:
                    message, address = s.recvfrom(1024)
                    message = message.decode()
                    if message == 'DISCOVER':
                        logger.debug(f"Received discovery message from {address}")

                        # Prepare response message
                        response = f"RECEIVER:{get_config().get('device_name', platform.node())}"

                        # Use UDP to send response
                        s.sendto(response.encode(), (address[0], LISTEN_PORT))
                        
                        # Handle device type after discovering the sender
                        self.handle_device_type()
                        break
                except Exception as e:
                    logger.error(f"Error in listenForBroadcast: {e}")
                sleep(1)  # Avoid busy-waiting

    def handle_device_type(self):
        print("Handling device type")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('0.0.0.0', RECEIVER_PORT))
            s.listen(1)
            logger.debug("Waiting for incoming connections...")
            self.receiver, addr = s.accept()
            logger.debug(f"Accepted connection from {addr}")

            # Exchange device information as JSON
            device_data = {
                "device_type": "python",
                "os": platform.system(),
                "ip": addr[0]
            }
            device_data_json = json.dumps(device_data)
            self.receiver.send(struct.pack('<Q', len(device_data_json)))
            self.receiver.send(device_data_json.encode())

            # Receive and process the device information from the sender
            device_json_size = struct.unpack('<Q', self.receiver.recv(8))[0]
            device_json = self.receiver.recv(device_json_size).decode()
            device_info = json.loads(device_json)
            sender_device_type = device_info.get("device_type", "unknown")

            if sender_device_type == "python":
                logger.info("Connected with Python device")
                # Start the file receiver and send the socket connection
                self.receiver.close()
                s.close()
                self.file_receiver = CreateUIForReceiver(device_info)
                self.hide()
                self.file_receiver.show()
            elif sender_device_type == "java":
                logger.info("Connected with Java device")
                # Handle Java device specific logic here
            else:
                logger.debug("Unknown device type received.")

    def center_window(self):
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        window_width, window_height = 800, 600
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2
        self.setGeometry(x, y, window_width, window_height)

    def updateProgressBar(self, value):
        self.progress_bar.setValue(value)
        if value >= 100:
            self.label.setText("File received successfully!")

    def decryptor_init(self, value):
        logger.debug("Received decrypt signal with filelist %s", value)
        if value:
            self.decryptor = Decryptor(value)
            self.decryptor.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    receive_app = StreamSignal()
    receive_app.show()
    sys.exit(app.exec())
