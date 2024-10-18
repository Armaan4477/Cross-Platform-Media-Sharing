import json
import platform
from PyQt6.QtWidgets import (
    QMessageBox, QWidget, QVBoxLayout, QPushButton, QListWidget, 
    QProgressBar, QLabel, QFileDialog, QApplication, QListWidgetItem, QTextEdit, QLineEdit,
    QHBoxLayout, QFrame
)
from PyQt6.QtGui import QScreen, QFont, QColor
from PyQt6.QtCore import QThread, pyqtSignal, Qt
import os
import socket
import struct
from constant import BROADCAST_ADDRESS, BROADCAST_PORT, LISTEN_PORT, get_config, logger
from crypt_handler import encrypt_file
from time import sleep

SENDER_DATA = 57000
RECEIVER_DATA = 58000

class FileSender(QThread):
    progress_update = pyqtSignal(int)
    file_send_completed = pyqtSignal(str)
    config = get_config()
    password = None

    def __init__(self, ip_address, file_paths, password=None, receiver_data=None):
        super().__init__()
        self.ip_address = ip_address
        self.file_paths = file_paths
        self.password = password
        self.receiver_data = receiver_data

    def initialize_connection(self):
        try:
            self.client_skt.close()
        except AttributeError:
            pass
        self.client_skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_skt.bind(('', SENDER_DATA))
            self.client_skt.connect((self.ip_address, RECEIVER_DATA))
        except ConnectionRefusedError:
            QMessageBox.critical(None, "Connection Error", "Failed to connect to the specified IP address.")
            return False
        except OSError as e:
            QMessageBox.critical(None, "Binding Error", f"Failed to bind to the specified port: {e}")
            return False
        return True

    def run(self):
        metadata_file_path = None
        self.metadata_created = False
        if not self.initialize_connection():
            return
        
        self.config = get_config()
        self.encryption_flag = self.config['encryption']

        for file_path in self.file_paths:
            if os.path.isdir(file_path):
                self.send_folder(file_path)
            else:
                if not self.metadata_created:
                    metadata_file_path = self.create_metadata(file_paths=self.file_paths)
                    self.send_file(metadata_file_path)
                self.send_file(file_path, encrypted_transfer=self.encryption_flag)
        
        if self.metadata_created and metadata_file_path:
            os.remove(metadata_file_path)
            
        logger.debug("Sent halt signal")
        self.client_skt.send('encyp: h'.encode())
        sleep(0.5)
        self.client_skt.send('encyp: h'.encode())
        sleep(0.5)
        self.client_skt.close()

    def create_metadata(self, folder_path=None, file_paths=None):
        if folder_path:
            metadata = []
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, folder_path)
                    file_size = os.path.getsize(file_path)
                    metadata.append({
                        'path': relative_path,
                        'size': file_size
                    })
                for dir in dirs:
                    dir_path = os.path.join(root, dir)
                    relative_path = os.path.relpath(dir_path, folder_path)
                    metadata.append({
                        'path': relative_path + '/',
                        'size': 0
                    })
            metadata.append({'base_folder_name': os.path.basename(folder_path), 'path': '.delete', 'size': 0})
            metadata_json = json.dumps(metadata)
            metadata_file_path = os.path.join(folder_path, 'metadata.json')
            with open(metadata_file_path, 'w') as f:
                f.write(metadata_json)
            self.metadata_created = True
            return metadata_file_path
        elif file_paths:
            metadata = []
            for file_path in file_paths:
                file_size = os.path.getsize(file_path)
                metadata.append({
                    'path': os.path.basename(file_path),
                    'size': file_size
                })
            metadata_json = json.dumps(metadata)
            metadata_file_path = os.path.join(os.path.dirname(file_paths[0]), 'metadata.json')
            with open(metadata_file_path, 'w') as f:
                f.write(metadata_json)
            self.metadata_created = True
            return metadata_file_path
            
    def send_folder(self, folder_path):
        print("Sending folder")
        
        if not self.metadata_created:
            metadata_file_path = self.create_metadata(folder_path=folder_path)
            metadata = json.loads(open(metadata_file_path).read())
            self.send_file(metadata_file_path)

        for file_info in metadata:
            relative_file_path = file_info['path']
            file_path = os.path.join(folder_path, relative_file_path)
            if not relative_file_path.endswith('.delete'):
                if file_info['size'] > 0:
                    if self.encryption_flag:
                        relative_file_path += ".crypt"
                    self.send_file(file_path, relative_file_path=relative_file_path, encrypted_transfer=self.encryption_flag)

        os.remove(metadata_file_path)

    def send_file(self, file_path, relative_file_path=None, encrypted_transfer=False):
        logger.debug("Sending file: %s", file_path)

        if encrypted_transfer:
            logger.debug("Encrypted transfer with password: %s", self.password)
            file_path = encrypt_file(file_path, self.password)

        sent_size = 0
        file_size = os.path.getsize(file_path)
        if relative_file_path is None:
            relative_file_path = os.path.basename(file_path)
        file_name_size = len(relative_file_path.encode())
        logger.debug("Sending %s, %s", relative_file_path, file_size)

        encryption_flag = 'encyp: t' if encrypted_transfer else 'encyp: f'

        self.client_skt.send(encryption_flag.encode())
        logger.debug("Sent encryption flag: %s", encryption_flag)

        self.client_skt.send(struct.pack('<Q', file_name_size))
        self.client_skt.send(relative_file_path.encode('utf-8'))
        self.client_skt.send(struct.pack('<Q', file_size))

        with open(file_path, 'rb') as f:
            while sent_size < file_size:
                data = f.read(4096)
                self.client_skt.sendall(data)
                sent_size += len(data)
                self.progress_update.emit(sent_size * 100 // file_size)

        if encrypted_transfer:
            os.remove(file_path)

        return True

class SendApp(QWidget):
    config = get_config()

    def __init__(self, ip_address, device_name, receiver_data):
        super().__init__()
        self.ip_address = ip_address
        self.device_name = device_name
        self.receiver_data = receiver_data
        self.file_paths = []
        self.initUI()

    def initUI(self):
        self.config = get_config()
        logger.debug("Encryption : %s", self.config['encryption'])
        self.setWindowTitle('DataDash: Send File')
        self.setFixedSize(960, 540)  # Updated to 16:9 ratio
        self.center_window()
        self.set_background()

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QFrame()
        header.setFixedHeight(70)
        header.setStyleSheet("background-color: #333; padding: 0px;")
        header_layout = QHBoxLayout(header)

        title_label = QLabel("DataDash: Send File")
        title_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        title_label.setStyleSheet("color: white;")
        header_layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout.addWidget(header)

        # Content area
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(20)

        # File selection buttons
        button_layout = QHBoxLayout()
        self.file_button = self.create_styled_button('Select Files')
        self.file_button.clicked.connect(self.selectFile)
        button_layout.addWidget(self.file_button)

        self.folder_button = self.create_styled_button('Select Folder')
        self.folder_button.clicked.connect(self.selectFolder)
        button_layout.addWidget(self.folder_button)

        content_layout.addLayout(button_layout)

        # File path display
        self.file_path_display = QTextEdit()
        self.file_path_display.setReadOnly(True)
        self.file_path_display.setStyleSheet("""
            QTextEdit {
                background-color: #2f3642;
                color: white;
                border: 1px solid #4b5562;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        content_layout.addWidget(self.file_path_display)

        # Password input (if encryption is enabled)
        if self.config['encryption']:
            password_layout = QHBoxLayout()
            self.password_label = QLabel('Encryption Password:')
            self.password_label.setStyleSheet("color: white; font-size: 14px;")
            password_layout.addWidget(self.password_label)

            self.password_input = QLineEdit()
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.password_input.setStyleSheet("""
                QLineEdit {
                    background-color: #2f3642;
                    color: white;
                    border: 1px solid #4b5562;
                    border-radius: 5px;
                    padding: 5px;
                }
            """)
            password_layout.addWidget(self.password_input)
            content_layout.addLayout(password_layout)

        # Send button
        self.send_button = self.create_styled_button('Send Files')
        self.send_button.setEnabled(False)
        self.send_button.clicked.connect(self.sendSelectedFiles)
        content_layout.addWidget(self.send_button, alignment=Qt.AlignmentFlag.AlignCenter)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #2f3642;
                color: white;
                border: 1px solid #4b5562;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
        content_layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: white; font-size: 14px;")
        self.style_label(self.status_label)
        content_layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignCenter)

         # Create 2 buttons for close and Transfer More Files
        # Keep them disabled until the file transfer is completed
        self.close_button = QPushButton('Close', self)
        self.close_button.setEnabled(False)
        self.close_button.setVisible(False)
        self.close_button.clicked.connect(self.close)
        content_layout.addWidget(self.close_button)

        self.transfer_more_button = QPushButton('Transfer More Files', self)
        self.transfer_more_button.setEnabled(False)
        self.transfer_more_button.setVisible(False)
        self.transfer_more_button.clicked.connect(self.transferMoreFiles)
        content_layout.addWidget(self.transfer_more_button)

        main_layout.addLayout(content_layout)
        self.setLayout(main_layout)

    def create_styled_button(self, text):
        button = QPushButton(text)
        button.setFixedSize(150, 50)
        button.setFont(QFont("Arial", 14))
        button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #2f3642,
                    stop: 1 #4b5562
                );
                color: white;
                border-radius: 25px;
                border: 1px solid rgba(0, 0, 0, 0.5);
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #3c4450,
                    stop: 1 #5a6476
                );
            }
            QPushButton:pressed {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #232933,
                    stop: 1 #414b58
                );
            }
            QPushButton:disabled {
                background: #666;
                color: #aaa;
            }
        """)
        return button

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

    def style_label(self, label):
        label.setStyleSheet("""
            color: #FFFFFF;
            background-color: transparent;  /* Set the background to transparent */
        """)

    def center_window(self):
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        window_width, window_height = 960, 540  # Updated to 16:9 ratio
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2
        self.setGeometry(x, y, window_width, window_height)

    def selectFile(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, 'Open Files')
        if file_paths:
            self.file_path_display.clear()
            for file_path in file_paths:
                self.file_path_display.append(file_path)
            self.file_paths = file_paths
            self.checkReadyToSend()

    def selectFolder(self):
        folder_path = QFileDialog.getExistingDirectory(self, 'Select Folder')
        if folder_path:
            self.file_path_display.clear()
            self.file_path_display.append(folder_path)
            self.file_paths = [folder_path]
            self.checkReadyToSend()

    def checkReadyToSend(self):
        if self.file_paths:
            self.send_button.setEnabled(True)

    

    def sendSelectedFiles(self):
        password = None

        if self.config['encryption']:
            password = self.password_input.text()
            if not password:
                QMessageBox.critical(None, "Password Error", "Please enter a password.")
                return

        self.send_button.setEnabled(False)
        self.file_sender = FileSender(self.ip_address, self.file_paths, password, self.receiver_data)
        self.file_sender.progress_update.connect(self.updateProgressBar)
        self.file_sender.file_send_completed.connect(self.fileSent)
        self.file_sender.start()

    def updateProgressBar(self, value):
        self.progress_bar.setValue(value)
        if value >= 100:
            self.status_label.setText("File transfer completed!")
            self.status_label.setStyleSheet("color: white; font-size: 14px; background-color: transparent;")

            
            # Enable the close and Transfer More Files buttons
            self.close_button.setEnabled(True)
            self.transfer_more_button.setEnabled(True)
            self.close_button.setVisible(True)
            self.transfer_more_button.setVisible(True)

    def transferMoreFiles(self):
        from broadcast import Broadcast
        # Go back to main menu and close all other sockets and threads
        self.close()
        self.broadcast_app = Broadcast()
        self.broadcast_app.show()

    def fileSent(self, file_path):
        self.status_label.setText(f"File sent: {file_path}")

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    send_app = SendApp("127.0.0.1", "Test Device", None)
    send_app.show()
    sys.exit(app.exec())