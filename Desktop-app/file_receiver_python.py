import os
import socket
import struct
import json
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QMetaObject
from PyQt6.QtWidgets import QMessageBox, QWidget, QVBoxLayout, QLabel, QProgressBar, QApplication
from PyQt6.QtGui import QScreen
from constant import get_config, logger
from crypt_handler import decrypt_file, Decryptor

SENDER_DATA = 57000
RECEIVER_DATA = 58000

class ReceiveWorkerPython(QThread):
    progress_update = pyqtSignal(int)
    decrypt_signal = pyqtSignal(list)
    password = None

    def __init__(self, client_ip):
        super().__init__()
        self.client_skt = None
        self.server_skt = None
        self.encrypted_files = []
        self.broadcasting = True
        self.metadata = None
        self.destination_folder = None
        self.store_client_ip = client_ip
        logger.debug(f"Client IP address stored: {self.store_client_ip}")

    def initialize_connection(self):
        # Close all previous server_sockets
        if self.server_skt:
            self.server_skt.close()
        self.server_skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # Bind the server socket to a local port
            self.server_skt.bind(('', RECEIVER_DATA))
            # Start listening for incoming connections
            self.server_skt.listen(1)
            print("Waiting for a connection...")
        except Exception as e:
            QMessageBox.critical(None, "Server Error", f"Failed to initialize the server: {str(e)}")
            return None

    def accept_connection(self):
        try:
            # Accept a connection from a client
            self.client_skt, self.client_address = self.server_skt.accept()
            print(f"Connected to {self.client_address}")
        except Exception as e:
            QMessageBox.critical(None, "Connection Error", f"Failed to accept connection: {str(e)}")
            return None

    def run(self):
        self.initialize_connection()
        self.accept_connection()
        if self.client_skt:
            self.receive_files()
        else:
            logger.error("Failed to establish a connection.")

    def receive_files(self):
        self.broadcasting = False  # Stop broadcasting

        while True:
            # Receive and decode encryption flag
            encryption_flag = self.client_skt.recv(8).decode()
            logger.debug("Received: %s", encryption_flag)

            if not encryption_flag:
                logger.debug("Dropped redundant data: %s", encryption_flag)
                break  # Drop redundant data

            if encryption_flag[-1] == 't':
                encrypted_transfer = True
            elif encryption_flag[-1] == 'h':
                # Halting signal, break transfer and decrypt files
                if self.encrypted_files:
                    self.decrypt_signal.emit(self.encrypted_files)
                self.encrypted_files = []
                break
            else:
                encrypted_transfer = False

            # Receive file name size
            file_name_size_data = self.client_skt.recv(8)
            file_name_size = struct.unpack('<Q', file_name_size_data)[0]
            
            if file_name_size == 0:
                break  # End of transfer signal

            # Receive file name
            file_name = self._receive_data(self.client_skt, file_name_size).decode()

            # Receive file size
            file_size_data = self.client_skt.recv(8)
            file_size = struct.unpack('<Q', file_size_data)[0]
            logger.debug("Receiving %s, %s bytes", file_name, file_size)

            received_size = 0

            if file_name == 'metadata.json':
                self.metadata = self.receive_metadata(file_size)
                self.destination_folder = self.create_folder_structure(self.metadata)
            else:
                file_path = self.get_file_path(file_name)
                if file_path.endswith('.delete'):
                    continue
                if self.metadata:
                    relative_path = self.get_relative_path_from_metadata(file_name)
                    file_path = os.path.join(self.destination_folder, relative_path)

                if encrypted_transfer:
                    self.encrypted_files.append(file_path)

                # Receive file data in chunks
                with open(file_path, "wb") as f:
                    while received_size < file_size:
                        chunk_size = min(4096, file_size - received_size)
                        data = self._receive_data(self.client_skt, chunk_size)
                        if not data:
                            break
                        f.write(data)
                        received_size += len(data)
                        self.progress_update.emit(received_size * 100 // file_size)

        self.broadcasting = True  # Resume broadcasting

    def _receive_data(self, socket, size):
        """Helper function to receive a specific amount of data."""
        received_data = b""
        while len(received_data) < size:
            chunk = socket.recv(size - len(received_data))
            if not chunk:
                raise ConnectionError("Connection closed before data was completely received.")
            received_data += chunk
        return received_data

    def receive_metadata(self, file_size):
        """Receive metadata from the sender."""
        received_data = self._receive_data(self.client_skt, file_size)
        try:
            metadata_json = received_data.decode('utf-8')
            return json.loads(metadata_json)
        except UnicodeDecodeError as e:
            logger.error("Unicode decode error: %s", e)
            raise
        except json.JSONDecodeError as e:
            logger.error("JSON decode error: %s", e)
            raise

    def create_folder_structure(self, metadata):
        """Create folder structure based on metadata."""
        # Get the default directory from configuration
        default_dir = get_config()["save_to_directory"]
        
        # Extract the base folder name from the last metadata entry
        top_level_folder = metadata[-1].get('base_folder_name', '')

        # Define the destination folder path
        destination_folder = os.path.join(default_dir, top_level_folder)
        
        # Create the destination folder if it does not exist
        os.makedirs(destination_folder, exist_ok=True)

        # Process each file info in metadata (excluding the last entry)
        for file_info in metadata[:-1]:  # Exclude the last entry (base folder info)
            # Skip any paths marked for deletion
            if file_info['path'] == '.delete':
                continue
            
            # Get the folder path from the file info
            folder_path = os.path.dirname(file_info['path'])
            
            # Create the full folder path
            full_folder_path = os.path.join(destination_folder, folder_path)
            
            # Create the directory if it does not exist
            if not os.path.exists(full_folder_path):
                os.makedirs(full_folder_path)

        return destination_folder

    def get_relative_path_from_metadata(self, file_name):
        """Get the relative path of a file from the metadata."""
        for file_info in self.metadata:
            if os.path.basename(file_info['path']) == file_name:
                return file_info['path']
        return file_name

    def get_file_path(self, file_name):
        """Get the file path for saving the received file."""
        default_dir = get_config()["save_to_directory"]
        if not default_dir:
            raise NotImplementedError("Unsupported OS")
        return os.path.join(default_dir, file_name)
    
    def close_connection(self):
        if self.client_skt:
            self.client_skt.close()
        if self.server_skt:
            self.server_skt.close()

class ReceiveAppP(QWidget):
    progress_update = pyqtSignal(int)

    def __init__(self, client_ip):
        super().__init__()
        self.client_ip = client_ip
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

        client_ip = self.client_ip
        self.file_receiver = ReceiveWorkerPython(client_ip)
        self.file_receiver.progress_update.connect(self.updateProgressBar)
        self.file_receiver.decrypt_signal.connect(self.decryptor_init)
        self.file_receiver.start()

        QMetaObject.invokeMethod(self.file_receiver, "start", Qt.ConnectionType.QueuedConnection)

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
    import sys
    app = QApplication(sys.argv)
    receive_app = ReceiveAppP()
    receive_app.show()
    app.exec()