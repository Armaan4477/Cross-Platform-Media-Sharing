import json
import platform
import tempfile
from pathlib import Path
from PyQt6.QtWidgets import (
    QMessageBox, QWidget, QVBoxLayout, QPushButton, QListWidget, 
    QProgressBar, QLabel, QFileDialog, QApplication, QListWidgetItem, QTextEdit, QLineEdit,
    QHBoxLayout, QFrame
)
from PyQt6.QtGui import QScreen, QFont, QColor, QKeyEvent, QKeySequence
from PyQt6.QtCore import QThread, pyqtSignal, Qt
import os
import socket
import struct
from constant import get_config, logger
from crypt_handler import encrypt_file
from time import sleep

SENDER_DATA = 57000
RECEIVER_DATA = 58000

class FileSender(QThread):
    progress_update = pyqtSignal(int)
    file_send_completed = pyqtSignal(str)
    transfer_finished = pyqtSignal()

    password = None

    def __init__(self, ip_address, file_paths, password=None, receiver_data=None):
        super().__init__()
        self.ip_address = ip_address
        self.file_paths = file_paths
        self.password = password
        self.receiver_data = receiver_data


    def initialize_connection(self):
        # Ensure previous socket is closed before re-binding
        try:
            if hasattr(self, 'client_skt'):
                self.client_skt.close()
                logger.debug("Socket closed successfully before rebinding.")
            sleep(1)  # Delay to ensure the OS releases the port
        except Exception as e:
            logger.error(f"Error closing socket: {e}")
        
        # Create a new TCP socket
        self.client_skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_skt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        #com.an.Datadash

        # Use dynamic port assignment to avoid WinError 10048
        try:
            self.client_skt.bind(('', 0))  # Bind to any available port assigned by the OS
            logger.debug(f"Bound to port {self.client_skt.getsockname()[1]}")  # Log the assigned port for debugging
            self.client_skt.connect((self.ip_address, RECEIVER_DATA))  # Connect to receiver's IP and port
            logger.debug(f"Successfully connected to {self.ip_address} on port {RECEIVER_DATA}")
        except ConnectionRefusedError:
            logger.error("Connection refused: Failed to connect to the specified IP address.")
            self.show_message_box("Connection Error", "Failed to connect to the specified IP address.")
            return False
        except OSError as e:
            logger.error(f"Binding error: {e}")
            self.show_message_box("Binding Error", f"Failed to bind to the specified port: {e}")
            return False

        return True



    def run(self):
        try:
            if self.client_skt:
                self.client_skt.close()
        except:
            pass

        metadata_file_path = None
        self.metadata_created = False
        if not self.initialize_connection():
            return
        
        self.encryption_flag = get_config()["encryption"]

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
        self.client_skt.close()
        self.transfer_finished.emit()
        #com.an.Datadash

    def get_temp_dir(self):
        system = platform.system()
        if system == "Windows":
            temp_dir = Path(os.getenv('LOCALAPPDATA')) / 'Temp' / 'DataDash'
        elif system == "Darwin":  # macOS
            temp_dir = Path.home() / 'Library' / 'Caches' / 'DataDash'
        elif system == "Linux":  # Linux and others
            temp_dir = Path.home() / '.cache' / 'DataDash'
        else:
            logger.error(f"Unsupported platform: {system}")
        
        try:
            os.makedirs(str(temp_dir), exist_ok=True)
            logger.debug(f"Created/verified temp directory: {temp_dir}")
        except Exception as e:
            logger.error(f"Failed to create temp directory: {e}")
            # Fallback to system temp directory
            temp_dir = Path(tempfile.gettempdir()) / 'DataDash'
            os.makedirs(str(temp_dir), exist_ok=True)
            logger.debug(f"Using fallback temp directory: {temp_dir}")
        
        return temp_dir

    def create_metadata(self, folder_path=None, file_paths=None):
        temp_dir = self.get_temp_dir()
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
            metadata_file_path = os.path.join(temp_dir, 'metadata.json')
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
            metadata_file_path = os.path.join(temp_dir, 'metadata.json')
            with open(metadata_file_path, 'w') as f:
                f.write(metadata_json)
            self.metadata_created = True
            return metadata_file_path
            
    def send_folder(self, folder_path):
        print("Sending folder")
        #com.an.Datadash
        
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
        #com.an.Datadash

        with open(file_path, 'rb') as f:
            while sent_size < file_size:
                data = f.read(4096)
                self.client_skt.sendall(data)
                sent_size += len(data)
                self.progress_update.emit(sent_size * 100 // file_size)

        if encrypted_transfer:
            os.remove(file_path)

        return True
    
    def closeEvent(self, event):
        #close all sockets and unbind the sockets
        self.client_skt.close()
        event.accept()

    def stop(self):
        """Sets the stop signal to True and closes the socket if it's open."""
        self.stop_signal = True
        if self.client_skt:
            try:
                self.client_skt.close()
            except Exception as e:
                logger.error(f"Error while closing socket: {e}")

class SendApp(QWidget):

    def __init__(self, ip_address, device_name, receiver_data):
        super().__init__()
        self.ip_address = ip_address
        self.device_name = device_name
        self.receiver_data = receiver_data
        self.file_paths = []
        self.initUI()
        self.progress_bar.setVisible(False)

    def initUI(self):
 
        logger.debug("Encryption : %s", get_config()["encryption"])
        self.setWindowTitle('DataDash: Send File')
        self.setFixedSize(853, 480)   # Updated to 16:9 ratio
        self.center_window()
        self.set_background()
        #com.an.Datadash

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
        content_layout.setSpacing(15)

        # File selection buttons
        button_layout = QHBoxLayout()
        self.file_button = self.create_styled_button('Select Files')
        self.file_button.clicked.connect(self.selectFile)
        button_layout.addWidget(self.file_button)

        self.folder_button = self.create_styled_button('Select Folder')
        self.folder_button.clicked.connect(self.selectFolder)
        button_layout.addWidget(self.folder_button)
        #com.an.Datadash

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
        if get_config()["encryption"]:
            password_layout = QHBoxLayout()
            self.password_label = QLabel('Encryption Password:')
            self.password_label.setStyleSheet("color: white; font-size: 14px; background-color: transparent;")
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
        self.send_button.setVisible(False)
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
        self.style_label(self.status_label)
        content_layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Keep them disabled until the file transfer is completed
        self.close_button = self.create_styled_button_close('Close')  # Apply styling here
        self.close_button.setVisible(False)
        self.close_button.clicked.connect(self.close)
        content_layout.addWidget(self.close_button)
        #com.an.Datadash

        self.mainmenu_button = self.create_styled_button_close('Main Menu')  # Apply styling here
        self.mainmenu_button.setVisible(False)
        self.mainmenu_button.clicked.connect(self.openMainWindow)
        content_layout.addWidget(self.mainmenu_button)

        main_layout.addLayout(content_layout)
        self.setLayout(main_layout)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.openMainWindow()

    def openMainWindow(self):
        from main import MainApp
        self.main_window = MainApp()
        self.main_window.show()
        self.close()

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
    
    def create_styled_button_close(self, text):
        button = QPushButton(text)
        button.setFixedHeight(25)
        button.setFont(QFont("Arial", 14))
        button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #2f3642,
                    stop: 1 #4b5562
                );
                color: white;
                border-radius: 8px;
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
            font-size: 20px;
        """)

    def center_window(self):
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        window_width, window_height = 853, 480  # Updated to 16:9 ratio
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2
        self.setGeometry(x, y, window_width, window_height)
        #com.an.Datadash

    def selectFile(self):
        documents= self.get_default_path()
        file_paths, _ = QFileDialog.getOpenFileNames(self, 'Open Files', documents)
        if file_paths:
            self.file_path_display.clear()
            for file_path in file_paths:
                self.file_path_display.append(file_path)
            self.file_paths = file_paths
            self.checkReadyToSend()

    def selectFolder(self):
        documents= self.get_default_path()
        folder_path = QFileDialog.getExistingDirectory(self, 'Select Folder', documents)
        if folder_path:
            self.file_path_display.clear()
            self.file_path_display.append(folder_path)
            self.file_paths = [folder_path]
            self.checkReadyToSend()

    def get_default_path(self):
        if platform.system() == 'Windows':
            return os.path.expanduser('~\\Documents')
        elif platform.system() == 'Linux':
            return os.path.expanduser('~/Documents')
        elif platform.system() == 'Darwin':  # macOS
            return os.path.expanduser('~/Documents')
        else:
            logger.error("Unsupported OS!")
            return os.path.expanduser('~')  # Fallback to home directory

    def checkReadyToSend(self):
        if self.file_paths:
            self.send_button.setVisible(True)
            #com.an.Datadash

    def sendSelectedFiles(self):
        password = None

        if get_config()["encryption"]:
            password = self.password_input.text()
            if not password:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Input Error")
                msg_box.setText("Please Enter a Password.")
                msg_box.setIcon(QMessageBox.Icon.Critical)
                msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)

                # Apply custom style with gradient background
                msg_box.setStyleSheet("""
                    QMessageBox {
                        background: qlineargradient(
                            x1: 0, y1: 0, x2: 1, y2: 1,
                            stop: 0 #b0b0b0,
                            stop: 1 #505050
                        );
                        color: #FFFFFF;
                        font-size: 16px;
                    }
                    QLabel {
                    background-color: transparent; /* Make the label background transparent */
                    }
                    QPushButton {
                        background: qlineargradient(
                            x1: 0, y1: 0, x2: 1, y2: 0,
                            stop: 0 rgba(47, 54, 66, 255),
                            stop: 1 rgba(75, 85, 98, 255)
                        );
                        color: white;
                        border-radius: 10px;
                        border: 1px solid rgba(0, 0, 0, 0.5);
                        padding: 4px;
                        font-size: 16px;
                    }
                    QPushButton:hover {
                        background: qlineargradient(
                            x1: 0, y1: 0, x2: 1, y2: 0,
                            stop: 0 rgba(60, 68, 80, 255),
                            stop: 1 rgba(90, 100, 118, 255)
                        );
                    }
                    QPushButton:pressed {
                        background: qlineargradient(
                            x1: 0, y1: 0, x2: 1, y2: 0,
                            stop: 0 rgba(35, 41, 51, 255),
                            stop: 1 rgba(65, 75, 88, 255)
                        );
                    }
                """)
                msg_box.exec()
            
                return

        self.send_button.setVisible(False)

        self.file_sender = FileSender(self.ip_address, self.file_paths, password, self.receiver_data)
        self.progress_bar.setVisible(True)
        self.file_sender.progress_update.connect(self.updateProgressBar)
        self.file_sender.file_send_completed.connect(self.fileSent)
        self.file_sender.transfer_finished.connect(self.onTransferFinished)
        self.file_sender.start()
        #com.an.Datadash

    def updateProgressBar(self, value):
        self.progress_bar.setValue(value)

    def fileSent(self, file_path):
        self.status_label.setText(f"File sent: {file_path}")

    def onTransferFinished(self):
        self.close_button.setVisible(True)
        self.status_label.setText("File transfer completed!")
        self.status_label.setStyleSheet("color: white; font-size: 18px; background-color: transparent;")
            

    def closeEvent(self, event):
        try:
            """Override the close event to ensure everything is stopped properly."""
            if self.file_sender and self.file_sender.isRunning():
                self.file_sender.stop()  # Signal the sender to stop
                self.file_sender.wait()  # Wait until the thread fully stops
        except Exception as e:
            pass
        finally:
            event.accept()

    def stop(self):
        """Sets the stop signal to True and closes the socket if it's open."""
        self.stop_signal = True
        if self.client_skt:
            try:
                self.client_skt.close()
            except Exception as e:
                logger.error(f"Error while closing socket: {e}")

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    send_app = SendApp("127.0.0.1", "Test Device", None)
    send_app.show()
    sys.exit(app.exec())
    #com.an.Datadash