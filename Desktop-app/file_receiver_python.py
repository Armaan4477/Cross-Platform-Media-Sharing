import os
import socket
import struct
import json
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QMessageBox, QWidget, QVBoxLayout, QLabel, QProgressBar, QApplication
from PyQt6.QtGui import QScreen
from constant import get_config, logger

SENDER_DATA = 57000
RECEIVER_DATA = 58000

class ReceiveWorkerPython(QThread):
    def __init__(self):
        super().__init__()
        self.client_socket = None
        self.data_socket = None
        self.encrypted_files = []
        self.broadcasting = True
        self.metadata = None
        self.destination_folder = None

    # def initialize_connection(self):
    #     self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #     self.client_socket.bind(('', SENDER_DATA))
    #     try:
    #         self.client_socket.connect((self.ip_address, RECEIVER_DATA))
    #     except ConnectionRefusedError:
    #         QMessageBox.critical(None, "Connection Error", "Failed to connect to the specified IP address.")
    #         return None
    def initialize_connection(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(('0.0.0.0', RECEIVER_DATA))

        self.server_socket.listen(5)  # Listen for multiple connections

        while True:
            self.client_socket, addr = self.server_socket.accept()
            #self.handle_device_type()
            #client_socket.close()  # Close the connection after receiving files

        logger.debug("List of encrypted files: %s", self.encrypted_files)

    def receive_files(self):
        self.broadcasting = False  # Stop broadcasting

        while True:
            try:
                # Receive and decode encryption flag
                encryption_flag = self.client_socket.recv(8).decode()
                logger.debug("Received: %s", encryption_flag)
                
                if not encryption_flag:
                    logger.debug("Dropped redundant data: %s", encryption_flag)
                    break  # Drop redundant data

                if encryption_flag[-1] == 't':
                    encrypted_transfer = True
                elif encryption_flag[-1] == 'h':
                    # Halting signal, break transfer and decrypt files
                    if self.encrypted_files:
                        # Placeholder for decryptor logic
                        pass
                    self.encrypted_files = []
                    break
                else:
                    encrypted_transfer = False

                # Receive file name size
                file_name_size_data = self.client_socket.recv(8)
                file_name_size = struct.unpack('<Q', file_name_size_data)[0]
                
                if file_name_size == 0:
                    break  # End of transfer signal

                # Receive file name
                file_name = self._receive_data(self.client_socket, file_name_size).decode()

                # Receive file size
                file_size_data = self.client_socket.recv(8)
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
                            data = self._receive_data(self.client_socket, chunk_size)
                            if not data:
                                break
                            f.write(data)
                            received_size += len(data)
                            # Placeholder for progress update logic

            except OSError as e:
                logger.error("Socket error: %s", e)
                break

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
        """Receive and parse metadata JSON file."""
        metadata = self._receive_data(self.client_socket, file_size).decode()
        return json.loads(metadata)

    def get_file_path(self, file_name):
        """Construct the file path from file name."""
        return os.path.join(os.path.expanduser("~"), "Downloads", file_name)

    def create_folder_structure(self, metadata):
        """Create directory structure for the incoming files."""
        base_folder = os.path.join(os.path.expanduser("~"), "Downloads", metadata['folder_name'])
        os.makedirs(base_folder, exist_ok=True)
        for folder in metadata.get('folders', []):
            os.makedirs(os.path.join(base_folder, folder), exist_ok=True)
        return base_folder

    def get_relative_path_from_metadata(self, file_name):
        """Get the relative path of the file from the metadata."""
        return self.metadata['files'].get(file_name, file_name)
