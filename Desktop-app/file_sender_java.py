import json
import platform
from PyQt6.QtWidgets import (
    QMessageBox, QWidget, QVBoxLayout, QPushButton, QListWidget, 
    QProgressBar, QLabel, QFileDialog, QApplication, QListWidgetItem, QTextEdit, QLineEdit
)
from PyQt6.QtGui import QScreen
import os
import socket
import struct
from PyQt6.QtCore import QThread, pyqtSignal
from constant import BROADCAST_ADDRESS, BROADCAST_PORT, LISTEN_PORT, get_config, logger
from crypt_handler import encrypt_file
from time import sleep

SENDER_DATA = 57000
RECEIVER_DATA = 58000

class FileSenderJava(QThread):
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
        # Close all previous sockets
        try:
            self.client_skt.close()
        except AttributeError:
            pass
        self.client_skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # Bind the socket to SENDER_DATA port
            self.client_skt.bind(('', SENDER_DATA))
            # Connect to the receiver on RECEIVER_DATA port
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
        metadata_file_path = None
        if not self.initialize_connection():
            return
        
        # Reload config on each file transfer session
        self.config = get_config()

        self.encryption_flag = self.config['encryption']
        # logger.debug("Encryption flag: %s", self.encryption_flag)

        for file_path in self.file_paths:
            if os.path.isdir(file_path):
                self.send_folder(file_path)
            else:
                if not self.metadata_created:
                    metadata_file_path = self.create_metadata(file_paths=self.file_paths)
                    self.send_file(metadata_file_path)
                self.send_file(file_path, encrypted_transfer=self.encryption_flag)
        
        # Delete metadata file
        if self.metadata_created and metadata_file_path:
            os.remove(metadata_file_path)
            
        logger.debug("Sent halt signal")
        self.client_skt.send('encyp: h'.encode())
        sleep(0.5)
        self.client_skt.send('encyp: h'.encode())
        sleep(0.5)
        self.client_skt.close()

    def create_metadata(self, folder_path=None,file_paths=None):
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
                        'size': 0  # Size is 0 for directories
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
            # Send metadata file
            self.send_file(metadata_file_path)

        # Send all files
        for file_info in metadata:
            relative_file_path = file_info['path']
            file_path = os.path.join(folder_path, relative_file_path)
            if not relative_file_path.endswith('.delete'):
                if file_info['size'] > 0:
                    if self.encryption_flag:
                        relative_file_path += ".crypt"
                    self.send_file(file_path, relative_file_path=relative_file_path, encrypted_transfer=self.encryption_flag)
                else:
                    # Handle directory creation (if needed, in receiver)
                    pass

        # Clean up metadata file
        os.remove(metadata_file_path)

    def send_file(self, file_path, relative_file_path=None, encrypted_transfer=False):
        logger.debug("Sending file: %s", file_path)
        # if self.metadata_created:
        #     self.createmetadata(file_path=file_path)

        # Encrypt the file if encrypted_transfer argument is present
        if encrypted_transfer:
            logger.debug("Encrypted transfer with password: %s", self.password)

            file_path = encrypt_file(file_path, self.password)

        sent_size = 0
        file_size = os.path.getsize(file_path)
        if relative_file_path is None:
            relative_file_path = os.path.basename(file_path)  # Default to the base name if relative path isn't provided
        file_name_size = len(relative_file_path.encode())
        logger.debug("Sending %s, %s", relative_file_path, file_size)

        encryption_flag = 'encyp: t' if encrypted_transfer else 'encyp: f'

        self.client_skt.send(encryption_flag.encode())
        logger.debug("Sent encryption flag: %s", encryption_flag)

        # Send the relative file path size and the path
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

class Receiver(QListWidgetItem):
    def __init__(self, name, ip_address):
        super().__init__(f"{name} ({ip_address})")
        self._name = name
        self._ip_address = ip_address
    
    @property
    def name(self):
        return self._name
    
    @name.setter
    def name(self, value):
        self._name = value
        self.updateText()
    
    @property
    def ip_address(self):
        return self._ip_address
    
    @ip_address.setter
    def ip_address(self, value):
        self._ip_address = value
        self.updateText()
    
    def updateText(self):
        self.setText(f"{self._name} ({self._ip_address})")

class SendAppJava(QWidget):
    config = get_config()

    def __init__(self,ip_address,device_name,receiver_data):
        self.ip_address = ip_address
        self.device_name = device_name
        self.receiver_data = receiver_data
        super().__init__()
        self.initUI()

    def initUI(self):
        self.config = get_config()
        logger.debug("Encryption : %s", self.config['encryption'])
        self.setWindowTitle('Send File')
        self.setGeometry(100, 100, 400, 300)
        self.center_window()

        layout = QVBoxLayout()

        file_selection_layout = QVBoxLayout()
        self.file_button = QPushButton('Select Files', self)
        self.file_button.clicked.connect(self.selectFile)
        file_selection_layout.addWidget(self.file_button)

        #Create a button for folder selection
        self.folder_button = QPushButton('Select Folder', self)
        self.folder_button.clicked.connect(self.selectFolder)
        file_selection_layout.addWidget(self.folder_button)

        self.file_paths = []

        self.file_path_display = QTextEdit(self)
        self.file_path_display.setReadOnly(True)
        file_selection_layout.addWidget(self.file_path_display)

        layout.addLayout(file_selection_layout)

        if self.config['encryption']:
            self.password_label = QLabel('Encryption Password:', self)
            layout.addWidget(self.password_label)

            self.password_input = QLineEdit(self)
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            layout.addWidget(self.password_input)

        self.send_button = QPushButton('Send Files', self)
        self.send_button.setEnabled(False)
        self.send_button.clicked.connect(self.sendSelectedFiles)
        layout.addWidget(self.send_button)

        self.progress_bar = QProgressBar(self)
        layout.addWidget(self.progress_bar)

        self.label = QLabel("", self)
        layout.addWidget(self.label)

        self.setLayout(layout)

    def center_window(self):
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        window_width, window_height = 800, 600
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
            print(self.file_paths)
            self.checkReadyToSend()

    def checkReadyToSend(self):
        if self.file_paths:
            self.send_button.setEnabled(True)

    def sendSelectedFiles(self):
        selected_item = self.device_name
        password = None

        if not selected_item:
            QMessageBox.critical(None, "Selection Error", "Please select a device to send the file.")
            return
        ip_address = self.ip_address
        print(self.file_paths)

        if self.config['encryption']:
            password = self.password_input.text()
            if not self.password_input.text():
                QMessageBox.critical(None, "Password Error", "Please enter a password.")
                return

        self.send_button.setEnabled(False)
        self.file_sender_java = FileSenderJava(ip_address, self.file_paths, password, self.receiver_data)
        self.file_sender_java.progress_update.connect(self.updateProgressBar)
        self.file_sender_java.file_send_completed.connect(self.fileSent)
        self.file_sender_java.start()

    def updateProgressBar(self, value):
        self.progress_bar.setValue(value)
        if value >= 100:
            self.label.setText("File transfer completed!")

    def fileSent(self, file_path):
        self.label.setText(f"File sent: {file_path}")

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    send_app = SendAppJava()
    send_app.show()
    sys.exit(app.exec())