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
    progress_update = pyqtSignal(int)
    decrypt_signal = pyqtSignal(list)
    password = None

    def __init__(self, client_ip):
        super().__init__()
        self.client_socket = None
        self.server_socket = None
        self.encrypted_files = []
        self.broadcasting = True
        self.metadata = None
        self.destination_folder = None
        self.store_client_ip = client_ip
        logger.debug(f"Client IP address stored: {self.store_client_ip}")

    def initialize_connection(self):
        # Close all previous server_sockets
        if self.server_socket:
            self.server_socket.close()
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # Bind the server socket to a local port
            self.server_socket.bind(('', RECEIVER_DATA))
            # Start listening for incoming connections
            self.server_socket.listen(1)
            print("Waiting for a connection...")
        except Exception as e:
            QMessageBox.critical(None, "Server Error", f"Failed to initialize the server: {str(e)}")
            return None

    def accept_connection(self):
        try:
            # Accept a connection from a client
            self.client_socket, self.client_address = self.server_socket.accept()
            print(f"Connected to {self.client_address}")
        except Exception as e:
            QMessageBox.critical(None, "Connection Error", f"Failed to accept connection: {str(e)}")
            return None

    def run(self):
        self.initialize_connection()
        self.accept_connection()
        if self.client_socket:
            self.receive_files()
        else:
            logger.error("Failed to establish a connection.")

    def receive_files(self):
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
    
    def close_connection(self):
        if self.client_socket:
            self.client_socket.close()
        if self.server_socket:
            self.server_socket.close()