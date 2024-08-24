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

RECEIVER_PORT = 12348

class FileReceiver(QThread):
    progress_update = pyqtSignal(int)
    decrypt_signal = pyqtSignal(list)
    password = None

    def __init__(self):
        super().__init__()
        self.encrypted_files = []
        self.broadcasting = True
        self.metadata = None
        self.destination_folder = None

    def run(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(('0.0.0.0', RECEIVER_PORT))

        self.server_socket.listen(5)  # Listen for multiple connections

        while True:
            self.client_socket, addr = self.server_socket.accept()
            self.handle_device_type()
            #client_socket.close()  # Close the connection after receiving files

        logger.debug("List of encrypted files: %s", self.encrypted_files)

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

        # Receive and process the device information from the sender
        device_json_size = struct.unpack('<Q', self.client_socket.recv(8))[0]
        device_json = self.client_socket.recv(device_json_size).decode()
        self.device_info = json.loads(device_json)
        sender_device_type = self.device_info.get("device_type", "unknown")
        if sender_device_type == "python":
            self.receive_files()
            self.client_socket.close()
        elif sender_device_type == "java":
            logger.debug("Connected to a Java device, but this feature is not implemented yet.")
            # You can handle Java-specific operations here if needed
        else:
            logger.debug("Unknown device type received.")

    def receive_files(self):
        self.broadcasting = False  # Stop broadcasting

        while True:
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
                    self.decrypt_signal.emit(self.encrypted_files)
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
                        self.progress_update.emit(received_size * 100 // file_size)

        self.broadcasting = True  # Resume broadcasting

    # def receive_files_swift(self, client_socket):
    #     self.broadcasting = False  # Stop broadcasting

    #     while True:
    #     # Receive file name size
    #        file_name_size_data = client_socket.recv(8)
    #        if len(file_name_size_data) < 8:
    #            logger.error("Received incomplete data for file name size: %s bytes", len(file_name_size_data))
    #            break  # Handle the case where we receive less than 8 bytes

    #        file_name_size = struct.unpack('<Q', file_name_size_data)[0]
    #        if file_name_size == 0:
    #            break  # End of transfer signal

    #        file_name = client_socket.recv(file_name_size).decode()
    #        file_size = struct.unpack('<Q', client_socket.recv(8))[0]

    #        logger.debug("Receiving %s, %s bytes", file_name, file_size)

    #        received_size = 0

    #        if file_name == 'metadata.json':
    #            self.metadata = self.receive_metadata(client_socket, file_size)
    #            self.destination_folder = self.create_folder_structure(self.metadata)
    #        else:
    #            file_path = self.get_file_path(file_name)
    #            if file_path.endswith('.delete'):
    #                continue
    #            if self.metadata:
    #                relative_path = self.get_relative_path_from_metadata(file_name)
    #                file_path = os.path.join(self.destination_folder, relative_path)

    #            with open(file_path, "wb") as f:
    #                while received_size < file_size:
    #                    data = client_socket.recv(4096)
    #                    if not data:
    #                        break
    #                    f.write(data)
    #                    received_size += len(data)
    #                    self.progress_update.emit(received_size * 100 // file_size)

    #     self.broadcasting = True  # Resume broadcasting
    

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
        received_data = self._receive_data(self.client_socket, file_size)
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

        self.file_receiver = FileReceiver()
        self.file_receiver.progress_update.connect(self.updateProgressBar)
        self.file_receiver.decrypt_signal.connect(self.decryptor_init)
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
