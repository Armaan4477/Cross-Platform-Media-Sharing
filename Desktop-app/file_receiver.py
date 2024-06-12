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

RECEIVER_PORT = 12348

class FileReceiver(QThread):
    progress_update = pyqtSignal(int)
    decrypt_signal = pyqtSignal(list)
    password = None

    def __init__(self, app_instance):
        super().__init__()
        self.app_instance = app_instance
        self.encrypted_files = []

    def run(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(('0.0.0.0', RECEIVER_PORT))

        server_socket.listen(5)  # Listen for multiple connections

        while True:
            client_socket, addr = server_socket.accept()
            self.receive_files(client_socket)
            client_socket.close()  # Close the connection after receiving files

        logger.debug("List of encrypted files: %s", self.encrypted_files)

    def receive_files(self, client_socket):
        while True:
            encryption_flag = client_socket.recv(8)
            if not encryption_flag:
                logger.debug("Dropped redundant data: %s", encryption_flag)
                break # Drop redundant data

            encryption_flag = encryption_flag.decode()

            logger.debug("Received: %s", encryption_flag)

            if encryption_flag[-1] == 't':
                encrypted_transfer = True
            elif encryption_flag[-1] == 'h':
                # h is the halting signal, break transfer and decrypt files
                if self.encrypted_files:
                    self.decrypt_signal.emit(self.encrypted_files)
                self.encrypted_files = []
                break
            else:
                encrypted_transfer = False

            # Receive file name size
            file_name_size_data = client_socket.recv(8)


            file_name_size = struct.unpack('<Q', file_name_size_data)[0]
            if file_name_size == 0:
                break  # End of transfer signal

            file_name = client_socket.recv(file_name_size).decode()
            file_size = struct.unpack('<Q', client_socket.recv(8))[0]

            logger.debug("Receiving %s, %s bytes", file_name, file_size)

            received_size = 0

            # Determine file path based on OS
            file_path = self.get_file_path(file_name)
            if encrypted_transfer:
                self.encrypted_files.append(file_path)

            with open(file_path, "wb") as f:
                while received_size < file_size:
                    data = client_socket.recv(4096)
                    if not data:
                        break
                    f.write(data)
                    received_size += len(data)
                    self.progress_update.emit(received_size * 100 // file_size)


    def get_file_path(self, file_name):
        default_dir = get_config()["save_to_directory"]
        if not default_dir:
            raise NotImplementedError("Unsupported OS")
        return os.path.join(default_dir, file_name)

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

        self.file_receiver = FileReceiver(self)
        self.file_receiver.progress_update.connect(self.updateProgressBar)
        self.file_receiver.decrypt_signal.connect(self.decryptor_init)
        self.file_receiver.start()

        threading.Thread(target=self.listenForBroadcast, daemon=True).start()

    def listenForBroadcast(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('', BROADCAST_PORT))

            while True:
                message, address = s.recvfrom(1024)
                message = message.decode()
                if message == 'DISCOVER':
                    response = f'RECEIVER:{get_config()["device_name"]}'
                    s.sendto(response.encode(), address)

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

