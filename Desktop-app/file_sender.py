from PyQt6.QtWidgets import (
    QMessageBox, QWidget, QVBoxLayout, QPushButton, QListWidget, 
    QProgressBar, QLabel, QFileDialog, QApplication, QListWidgetItem, QTextEdit
)
from PyQt6.QtGui import QScreen
import os
import socket
import struct
from PyQt6.QtCore import QThread, pyqtSignal
from constant import BROADCAST_ADDRESS, BROADCAST_PORT, LISTEN_PORT

RECEIVER_PORT = 12347

class FileSender(QThread):
    progress_update = pyqtSignal(int)
    file_send_completed = pyqtSignal(str)

    def __init__(self, ip_address, file_paths):
        super().__init__()
        self.ip_address = ip_address
        self.file_paths = file_paths

    def run(self):
        print(self.file_paths)
        for file_path in self.file_paths:
            if not self.send_file(file_path):
                return  # Stop if sending any file fails
            self.file_send_completed.emit(file_path)
        # Send a zero-size file name as the signal to end the transfer and close the connection
            self.client_socket.sendall(struct.pack('<Q', 0))
            self.client_socket.close()

    def send_file(self, file_path):
        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)
        file_name_size = len(file_name.encode())

        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_socket.connect((self.ip_address, RECEIVER_PORT))
        except ConnectionRefusedError:
            QMessageBox.critical(None, "Connection Error", "Failed to connect to the specified IP address.")
            return False

        self.client_socket.send(struct.pack('<Q', file_name_size))
        self.client_socket.send(file_name.encode())
        self.client_socket.send(struct.pack('<Q', file_size))

        sent_size = 0
        with open(file_path, 'rb') as f:
            while sent_size < file_size:
                data = f.read(4096)
                self.client_socket.sendall(data)
                sent_size += len(data)
                self.progress_update.emit(sent_size * 100 // file_size)

        # client_socket.sendall(struct.pack('<Q', 0))  # Send a zero-size file name as the signal to end the transfer
        # client_socket.close()
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

class SendApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Send File')
        self.setGeometry(100, 100, 400, 300)
        self.center_window()

        layout = QVBoxLayout()

        file_selection_layout = QVBoxLayout()
        self.file_button = QPushButton('Select Files', self)
        self.file_button.clicked.connect(self.selectFile)
        file_selection_layout.addWidget(self.file_button)

        self.file_paths = []

        self.file_path_display = QTextEdit(self)
        self.file_path_display.setReadOnly(True)
        file_selection_layout.addWidget(self.file_path_display)

        layout.addLayout(file_selection_layout)

        self.discover_button = QPushButton('Discover Devices', self)
        self.discover_button.clicked.connect(self.discoverDevices)
        layout.addWidget(self.discover_button)

        self.device_list = QListWidget(self)
        layout.addWidget(self.device_list)

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

    def discoverDevices(self):
        self.device_list.clear()
        receivers = self.discover_receivers()
        for receiver in receivers:
            item = Receiver(receiver['name'], receiver['ip'])
            self.device_list.addItem(item)
        self.checkReadyToSend()

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

    def checkReadyToSend(self):
        if self.file_paths and self.device_list.count() > 0:
            self.send_button.setEnabled(True)

    def sendSelectedFiles(self):
        selected_item = self.device_list.currentItem()
        if not selected_item:
            QMessageBox.critical(None, "Selection Error", "Please select a device to send the file.")
            return
        ip_address = selected_item.ip_address
        self.send_button.setEnabled(False)
        self.file_sender = FileSender(ip_address, self.file_paths)
        self.file_sender.progress_update.connect(self.updateProgressBar)
        self.file_sender.file_send_completed.connect(self.fileSent)
        self.file_sender.start()

    def updateProgressBar(self, value):
        self.progress_bar.setValue(value)
        if value >= 100:
            self.label.setText("File transfer completed!")

    def fileSent(self, file_path):
        self.label.setText(f"File sent: {file_path}")

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    send_app = SendApp()
    send_app.show()
    sys.exit(app.exec())
