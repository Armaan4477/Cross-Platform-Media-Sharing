import os
import socket
import struct
import json
from PyQt6 import QtCore
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QMetaObject,QTimer
from PyQt6.QtWidgets import QMessageBox, QWidget, QVBoxLayout, QLabel, QProgressBar, QApplication,QPushButton,QHBoxLayout
from PyQt6.QtGui import QScreen,QMovie,QFont
from constant import get_config, logger
from crypt_handler import decrypt_file, Decryptor
import subprocess
import platform

SENDER_DATA = 57000
RECEIVER_DATA = 58000

class ReceiveWorkerJava(QThread):
    progress_update = pyqtSignal(int)
    decrypt_signal = pyqtSignal(list)
    receiving_started = pyqtSignal()
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
            self.receiving_started.emit()
            self.receive_files()
        else:
            logger.error("Failed to establish a connection.")


    def receive_files(self):
        self.broadcasting = False  # Stop broadcasting
        logger.debug("File reception started.")

        while True:
            try:
                # Receive and decode encryption flag
                encryption_flag = self.client_skt.recv(8).decode()
                logger.debug("Received encryption flag: %s", encryption_flag)

                if not encryption_flag:
                    logger.debug("Dropped redundant data: %s", encryption_flag)
                    break

                if encryption_flag[-1] == 't':
                    encrypted_transfer = True
                elif encryption_flag[-1] == 'h':
                    # Halting signal, break transfer and decrypt files
                    if self.encrypted_files:
                        self.decrypt_signal.emit(self.encrypted_files)
                    self.encrypted_files = []
                    logger.debug("Received halt signal. Stopping file reception.")
                    break
                else:
                    encrypted_transfer = False

                # Receive file name size
                file_name_size_data = self.client_skt.recv(8)
                file_name_size = struct.unpack('<Q', file_name_size_data)[0]
                logger.debug("File name size received: %d", file_name_size)
                
                if file_name_size == 0:
                    logger.debug("End of transfer signal received.")
                    break  # End of transfer signal

                # Receive file name and normalize the path
                file_name = self._receive_data(self.client_skt, file_name_size).decode()

                # Convert Windows-style backslashes to Unix-style forward slashes
                file_name = file_name.replace('\\', '/')
                logger.debug("Normalized file name: %s", file_name)

                # Receive file size
                file_size_data = self.client_skt.recv(8)
                file_size = struct.unpack('<Q', file_size_data)[0]
                logger.debug("Receiving file %s, size: %d bytes", file_name, file_size)

                logger.debug("Reached 1")

                received_size = 0

                # Check if it's metadata
                if file_name == 'metadata.json':
                    logger.debug("Receiving metadata file.")
                    self.metadata = self.receive_metadata(file_size)
                    ## Check if the 2nd last position of metadata is "base_folder_name" and it exists
                    if self.metadata[-1].get('base_folder_name', '') and self.metadata[-1]['base_folder_name'] != '':
                        self.destination_folder = self.create_folder_structure(self.metadata)
                        logger.debug("Metadata processed. Destination folder set to: %s", self.destination_folder)
                    else:
                        ## If not, set the destination folder to the default directory
                        self.destination_folder = get_config()["save_to_directory"]
                    logger.debug("Metadata processed. Destination folder set to: %s", self.destination_folder)
                else:
                    try:
                        if self.destination_folder is None:
                            self.destination_folder = get_config()["save_to_directory"]
                        # Check if file exists in the receiving directory
                        original_name, extension = os.path.splitext(file_name)
                        logger.debug("Original name: %s, Extension: %s", original_name, extension)
                        i = 1
                        while os.path.exists(os.path.join(self.destination_folder, file_name)):
                            file_name = f"{original_name} ({i}){extension}"
                            logger.debug("File name already exists. Trying new name: %s", file_name)
                            i += 1
                    except Exception as e:
                        logger.error("Error while checking file existence: %s", str(e))
                        pass
                    # Determine the correct path using metadata
                    if self.metadata:
                        relative_path = self.get_relative_path_from_metadata(file_name)
                        file_path = os.path.join(self.destination_folder, relative_path)
                        logger.debug("Constructed file path from metadata: %s", file_path)
                    else:
                        # Fallback if metadata is not available
                        file_path = self.get_file_path(file_name)
                        logger.debug("Constructed file path without metadata: %s", file_path)

                    # Normalize the final file path
                    file_path = os.path.normpath(file_path)

                    # Ensure that the directory exists for the file
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    logger.debug("Directory structure created or verified for: %s", os.path.dirname(file_path))
                    logger.debug("Reached 4")

                    # Check for encrypted transfer
                    if encrypted_transfer:
                        self.encrypted_files.append(file_path)
                        logger.debug("File marked for decryption: %s", file_path)

                    # Receive file data in chunks
                    with open(file_path, "wb") as f:
                        while received_size < file_size:
                            chunk_size = min(4096, file_size - received_size)
                            data = self._receive_data(self.client_skt, chunk_size)
                            if not data:
                                logger.error("Failed to receive data. Connection may have been closed.")
                                break
                            f.write(data)
                            received_size += len(data)
                            logger.debug("Received %d/%d bytes for file %s", received_size, file_size, file_name)
                            self.progress_update.emit(received_size * 100 // file_size)

            except Exception as e:
                logger.error("Error during file reception: %s", str(e))
                break

        self.broadcasting = True  # Resume broadcasting
        logger.debug("File reception completed.")


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
        
        if not default_dir:
            raise ValueError("No save_to_directory configured")
        
        # Extract the base folder name from the last metadata entry
        top_level_folder = metadata[-1].get('base_folder_name', '')
        if not top_level_folder:
            raise ValueError("Base folder name not found in metadata")
        
        if "primary" in top_level_folder:
            top_level_folder = top_level_folder.replace("primary%3A", "")
            top_level_folder = top_level_folder.replace("%2F", "")
        
        top_level_folder = top_level_folder.split('/')[-1]

        # Define the initial destination folder path
        destination_folder = os.path.join(default_dir, top_level_folder)

        # Check if the destination folder already exists, and if it does, add a "(i)" suffix
        destination_folder = self._get_unique_folder_name(destination_folder)

        logger.debug("Destination folder: %s", destination_folder)

        # Create the destination folder if it does not exist
        if not os.path.exists(destination_folder):
            os.makedirs(destination_folder)
            logger.debug("Created base folder: %s", destination_folder)

        # Track created folders to avoid duplicates
        created_folders = set()
        created_folders.add(destination_folder)

        # Process each file info in metadata (excluding the last entry)
        for file_info in metadata[:-1]:  # Exclude the last entry (base folder info)
            # Skip any paths marked for deletion
            if file_info['path'] == '.delete':
                continue
            
            # Get the folder path from the file info
            folder_path = os.path.dirname(file_info['path'])
            if folder_path:
                # Create the full folder path
                full_folder_path = os.path.join(destination_folder, folder_path)
                
                # Check if the folder has already been created
                if full_folder_path not in created_folders:
                    # Ensure that the directory does not override existing data by getting a unique folder name
                    unique_folder_path = self._get_unique_folder_name(full_folder_path)
                    
                    # Create the directory if it does not exist
                    if not os.path.exists(unique_folder_path):
                        os.makedirs(unique_folder_path)
                        logger.debug("Created folder: %s", unique_folder_path)

                    # Add the folder to the set of created folders
                    created_folders.add(unique_folder_path)

        return destination_folder

    def _get_unique_folder_name(self, folder_path):
        """Append a unique (i) to folder name if it already exists."""
        base_folder_path = folder_path
        i = 1
        while os.path.exists(folder_path):
            folder_path = f"{base_folder_path} ({i})"
            i += 1
        return folder_path


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

class ReceiveAppPJava(QWidget):
    progress_update = pyqtSignal(int)

    def __init__(self, client_ip):
        super().__init__()
        self.client_ip = client_ip
        self.initUI()
        self.setFixedSize(853, 480)
        
        self.current_text = "Waiting for file..."  # The full text for the label
        self.displayed_text = ""  # Text that will appear with typewriter effect
        self.char_index = 0  # Keeps track of the character index for typewriter effect
        self.progress_bar.setVisible(False)  # Initially hidden
        
        self.file_receiver = ReceiveWorkerJava(client_ip)
        self.file_receiver.progress_update.connect(self.updateProgressBar)
        self.file_receiver.decrypt_signal.connect(self.decryptor_init)
        self.file_receiver.receiving_started.connect(self.show_progress_bar)  # Connect new signal
       
        
        # Start the typewriter effect
        self.typewriter_timer = QTimer(self)
        self.typewriter_timer.timeout.connect(self.update_typewriter_effect)
        self.typewriter_timer.start(100)  # Adjust speed of typewriter effect

        # Start the file receiving process and set progress bar visibility
        QMetaObject.invokeMethod(self.file_receiver, "start", Qt.ConnectionType.QueuedConnection)

    def initUI(self):
        self.setWindowTitle('Receive File')
        self.setGeometry(100, 100, 853, 480)
        self.center_window()
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #b0b0b0,
                    stop: 1 #505050
                );
            }
        """)

        # Define the relative paths to the GIFs
        receiving_gif_path = os.path.join(os.path.dirname(__file__), "assets", "file.gif")
        success_gif_path = os.path.join(os.path.dirname(__file__), "assets", "mark.gif")

        layout = QVBoxLayout()
        layout.setSpacing(10)  # Set spacing between widgets
        layout.setContentsMargins(10, 10, 10, 10)  # Add some margins around the layout

        # Loading label with the movie (GIF)
        self.loading_label = QLabel(self)
        self.loading_label.setStyleSheet("QLabel { background-color: transparent; border: none; }")
        self.receiving_movie = QMovie(receiving_gif_path)
        self.success_movie = QMovie(success_gif_path)  # New success GIF
        self.receiving_movie.setScaledSize(QtCore.QSize(100, 100))
        self.success_movie.setScaledSize(QtCore.QSize(100, 100))  # Set size for success GIF
        self.loading_label.setMovie(self.receiving_movie)
        self.receiving_movie.start()
        layout.addWidget(self.loading_label, alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)

        # Text label "Waiting for file..." (for typewriter effect)
        self.label = QLabel("", self)
        self.label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 28px;
                background: transparent;
                border: none;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.label, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

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
        layout.addWidget(self.progress_bar)

        # Open directory button
        self.open_dir_button = self.create_styled_button('Open Receiving Directory')
        self.open_dir_button.clicked.connect(self.open_receiving_directory)
        self.open_dir_button.setVisible(False)  # Initially hidden
        layout.addWidget(self.open_dir_button)

        # Keep them disabled until the file transfer is completed
        self.close_button = self.create_styled_button('Close')  # Apply styling here
        self.close_button.setVisible(False)
        self.close_button.clicked.connect(self.close)
        layout.addWidget(self.close_button)

        self.setLayout(layout)

    def create_styled_button(self, text):
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

    def center_window(self):
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        window_width, window_height = 853, 480
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2
        self.setGeometry(x, y, window_width, window_height)

    def show_progress_bar(self):
        self.progress_bar.setVisible(True)

    
    def update_typewriter_effect(self):
        """Updates the label text one character at a time."""
        if self.char_index < len(self.current_text):
            self.displayed_text += self.current_text[self.char_index]
            self.label.setText(self.displayed_text)
            self.char_index += 1
        else:
            # Stop the timer when the entire text is displayed
            self.typewriter_timer.stop()

    def updateProgressBar(self, value):
        self.progress_bar.setValue(value)
        if value >= 100:
            self.label.setText("File received successfully!")
            self.open_dir_button.setVisible(True)  # Show the button when file is received
            self.change_gif_to_success()  # Change GIF to success animation
            self.close_button.setVisible(True)

    def change_gif_to_success(self):
        self.receiving_movie.stop()
        self.loading_label.setMovie(self.success_movie)
        self.success_movie.start()

    def decryptor_init(self, value):
        logger.debug("Received decrypt signal with filelist %s", value)
        if value:
            self.decryptor = Decryptor(value)
            self.decryptor.show()

    def open_receiving_directory(self):
        config = get_config()
        receiving_dir = config.get("save_to_directory")
        
        if receiving_dir:
            try:
                current_os = platform.system()
                
                if current_os == 'Windows':
                    os.startfile(receiving_dir)
                elif current_os == 'Linux':
                    subprocess.Popen(["xdg-open", receiving_dir])
                elif current_os == 'Darwin':  # macOS
                    subprocess.Popen(["open", receiving_dir])
                else:
                    raise NotImplementedError(f"Unsupported OS: {current_os}")
            
            except Exception as e:
                logger.error("Failed to open directory: %s", str(e))

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    receive_app = ReceiveAppPJava()
    receive_app.show()
    app.exec()