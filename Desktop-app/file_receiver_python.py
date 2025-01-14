import os
import socket
import struct
import json
import subprocess
import platform
from PyQt6 import QtCore
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QMetaObject, QTimer
from PyQt6.QtWidgets import QMessageBox, QWidget, QVBoxLayout, QLabel, QProgressBar,QSizePolicy, QApplication, QPushButton, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QStyledItemDelegate
from PyQt6.QtGui import QScreen, QMovie, QFont, QKeyEvent, QKeySequence
from constant import ConfigManager
from loges import logger
from crypt_handler import decrypt_file, Decryptor
import time
import shutil
from portsss import RECEIVER_DATA_DESKTOP, CHUNK_SIZE_DESKTOP

class ProgressBarDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        if index.column() == 3:
            progress = index.data(Qt.ItemDataRole.UserRole)
            if progress is not None:
                progressBar = QProgressBar()
                progressBar.setStyleSheet("""
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
                progressBar.setGeometry(option.rect)
                progressBar.setValue(progress)
                progressBar.setTextVisible(True)
                painter.save()
                painter.translate(option.rect.topLeft())
                progressBar.render(painter)
                painter.restore()
            return
        super().paint(painter, option, index)

    def createEditor(self, parent, option, index):
        return None  # Disable editing

class ReceiveWorkerPython(QThread):
    progress_update = pyqtSignal(int)  # Overall progress
    file_progress_update = pyqtSignal(str, int)  # Individual file progress (filename, progress)
    decrypt_signal = pyqtSignal(list)
    close_connection_signal = pyqtSignal()
    receiving_started = pyqtSignal()
    transfer_finished = pyqtSignal()
    password = None
    update_files_table_signal = pyqtSignal(list)
    # Add new signal for file rename events
    file_renamed_signal = pyqtSignal(str, str)  # old_name, new_name
    # Add new signal
    transfer_stats_update = pyqtSignal(float, float, float)  # speed, eta, elapsed
    file_count_update = pyqtSignal(int, int, int)  # total_files, files_received, files_pending

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
        self.close_connection_signal.connect(self.close_connection)
        self.config_manager = ConfigManager()
        self.config_manager.start()
        #com.an.Datadash
        self.start_time = None
        self.last_update_time = None
        self.last_bytes_received = 0
        self.total_bytes_received = 0
        self.total_files = 0
        self.files_received = 0

    def initialize_connection(self):
        """Initialize server socket with proper reuse settings"""
        try:
            # Close existing sockets
            if self.server_skt:
                try:
                    self.server_skt.shutdown(socket.SHUT_RDWR)
                    self.server_skt.close()
                except:
                    pass

            self.server_skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # Set socket options
            self.server_skt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if platform.system() != 'Windows':
                try:
                    self.server_skt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                except AttributeError:
                    logger.debug("SO_REUSEPORT not available on this platform")

            # Configure timeout
            self.server_skt.settimeout(60)

            # Bind and listen
            self.server_skt.bind(('', RECEIVER_DATA_DESKTOP))
            self.server_skt.listen(1)
            logger.debug("Server initialized on port %d", RECEIVER_DATA_DESKTOP)

        except OSError as e:
            if e.errno == 48:  # Address already in use
                logger.error("Port %d is in use, waiting to retry...", RECEIVER_DATA_DESKTOP)
                time.sleep(1)
                self.initialize_connection()
            else:
                raise
        except Exception as e:
            logger.error("Failed to initialize server: %s", str(e))
            raise

    def accept_connection(self):
        if self.client_skt:
            self.client_skt.close()
        try:
            # Accept a connection from a client
            self.client_skt, self.client_address = self.server_skt.accept()
            print(f"Connected to {self.client_address}")
        except Exception as e:
            error_message = f"Failed to accept connection: {str(e)}"
            logger.error(error_message)
            self.error_occurred.emit("Connection Error", error_message, "")
            return None

    def run(self):
        self.initialize_connection()
        self.accept_connection()
        if self.client_skt:
            self.receiving_started.emit()
            self.receive_files()
        else:
            logger.error("Failed to establish a connection.")

        if self.client_skt:
            self.client_skt.close()
        if self.server_skt:
            self.server_skt.close()

    def receive_files(self):
        self.start_time = time.time()
        self.last_update_time = time.time()
        self.broadcasting = False
        self.folder_transfer = False
        logger.debug("File reception started.")
        
        total_bytes = 0
        received_total = 0
        folder_received_bytes = 0
        encrypted_transfer = False
        file_name = None  # Initialize file_name
        original_filename = None  # Initialize original_filename

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
                    if self.encrypted_files:
                        self.decrypt_signal.emit(self.encrypted_files)
                    self.encrypted_files = []
                    logger.debug("Received halt signal. Stopping file reception.")
                    self.transfer_finished.emit()
                    break
                else:
                    encrypted_transfer = False

                # Receive file name size
                file_name_size_data = self.client_skt.recv(8)
                file_name_size = struct.unpack('<Q', file_name_size_data)[0]
                logger.debug("File name size received: %d", file_name_size)

                if file_name_size == 0:
                    logger.debug("End of transfer signal received.")
                    break

                # Receive file name and normalize the path
                file_name = self._receive_data(self.client_skt, file_name_size).decode()
                original_filename = file_name  # Store original filename before any modifications

                # Add .crypt extension for encrypted files
                if encrypted_transfer and file_name != 'metadata.json':
                    file_name = file_name + '.crypt'

                # Convert Windows-style backslashes to Unix-style forward slashes
                file_name = file_name.replace('\\', '/')
                logger.debug("Normalized file name: %s", file_name)

                # Receive file size
                file_size_data = self.client_skt.recv(8)
                file_size = struct.unpack('<Q', file_size_data)[0]
                logger.debug("Receiving file %s, size: %d bytes", file_name, file_size)

                received_size = 0

                # Check if it's metadata
                if file_name == 'metadata.json':
                    logger.debug("Receiving metadata file.")
                    self.metadata = self.receive_metadata(file_size)
                    # Calculate total bytes from metadata
                    total_bytes = sum(file_info['size'] for file_info in self.metadata 
                                    if file_info.get('size', 0) > 0 and file_info.get('path') != '.delete')
                    logger.debug(f"Total bytes to receive: {total_bytes}")
                    
                    if total_bytes == 0:
                        total_bytes = 1  # Prevent division by zero
                        
                    ## Check if the 2nd last position of metadata is "base_folder_name" and it exists
                    if self.metadata[-1].get('base_folder_name', '') and self.metadata[-1]['base_folder_name'] != '':
                        self.folder_transfer = True
                        self.destination_folder = self.create_folder_structure(self.metadata)
                    else:
                        ## If not, set the destination folder to the default directory
                        self.destination_folder = self.config_manager.get_config()["save_to_directory"]
                    logger.debug("Metadata processed. Destination folder set to: %s", self.destination_folder)
                else:
                    # Check if file exists in the receiving directory
                    original_name = file_name
                    original_name_base, extension = os.path.splitext(file_name)
                    i = 1
                    while os.path.exists(os.path.join(self.destination_folder, file_name)):
                        if encrypted_transfer:
                            file_name = f"{original_name_base[:-6]} ({i}).crypt"  # Remove .crypt before adding counter
                        else:
                            file_name = f"{original_name_base} ({i}){extension}"
                        i += 1
                    
                    # Emit signal if file was renamed, use original filename for display
                    if file_name != original_name:
                        display_name = original_filename if encrypted_transfer else file_name
                        self.file_renamed_signal.emit(original_filename, display_name)

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

                    # Check for encrypted transfer
                    if encrypted_transfer:
                        self.encrypted_files.append(file_path)
                        logger.debug("File marked for decryption: %s", file_path)

                    # Receive file data in chunks
                    with open(file_path, "wb") as f:
                        while received_size < file_size:
                            current_time = time.time()
                            chunk_size = min(CHUNK_SIZE_DESKTOP, file_size - received_size)
                            data = self._receive_data(self.client_skt, chunk_size)
                            if not data:
                                logger.error("Failed to receive data. Connection may have been closed.")
                                break
                            f.write(data)
                            received_size += len(data)
                            received_total += len(data)
                            self.total_bytes_received = received_total
                            
                            # Calculate transfer statistics every 0.5 seconds
                            if current_time - self.last_update_time >= 0.5:
                                elapsed = current_time - self.start_time
                                speed = (received_total - self.last_bytes_received) / (current_time - self.last_update_time) / (1024 * 1024)  # MB/s
                                remaining_bytes = total_bytes - received_total
                                eta = remaining_bytes / (speed * 1024 * 1024) if speed > 0 else 0
                                
                                self.transfer_stats_update.emit(speed, eta, elapsed)
                                self.last_update_time = current_time
                                self.last_bytes_received = received_total
                            
                            if self.folder_transfer:
                                folder_received_bytes += len(data)
                                folder_total = sum(file_info.get('size', 0) for file_info in self.metadata[:-1]
                                                 if file_info.get('path') != '.delete')
                                folder_progress = (folder_received_bytes * 100) // folder_total if folder_total > 0 else 0
                                folder_progress = min(folder_progress, 100)
                                self.file_progress_update.emit("folder_progress", folder_progress)
                            
                            # Safe progress calculation
                            try:
                                file_progress = (received_size * 100) // file_size if file_size > 0 else 0
                                overall_progress = (received_total * 100) // total_bytes if total_bytes > 0 else 0
                                
                                # Ensure progress doesn't exceed 100%
                                file_progress = min(file_progress, 100)
                                overall_progress = min(overall_progress, 100)
                                
                                if not self.folder_transfer:
                                    # Use original filename for progress updates if encrypted
                                    progress_name = original_filename if encrypted_transfer else file_name
                                    self.file_progress_update.emit(progress_name, file_progress)
                                self.progress_update.emit(overall_progress)
                            except Exception as e:
                                logger.error(f"Error calculating progress: {str(e)}")

                    self.files_received += 1
                    files_pending = self.total_files - self.files_received
                    self.file_count_update.emit(self.total_files, self.files_received, files_pending)

            except ZeroDivisionError as zde:
                logger.error(f"Division by zero error: {str(zde)}")
                continue
            except Exception as e:
                logger.error("Error during file reception: %s", str(e))
                break

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
    #com.an.Datadash

    def receive_metadata(self, file_size):
        """Receive metadata from the sender."""
        received_data = self._receive_data(self.client_skt, file_size)
        try:
            metadata_json = received_data.decode('utf-8')
            metadata = json.loads(metadata_json)
            
            # Only emit the folder information if it's a folder transfer
            if metadata and metadata[-1].get('base_folder_name', ''):
                # Send only the folder metadata entry
                self.update_files_table_signal.emit([metadata[-1]])
            else:
                # Send full metadata for individual files
                self.update_files_table_signal.emit(metadata)
                
            # Count total files from metadata
            if metadata and metadata[-1].get('base_folder_name', ''):
                # For folder transfers, count all files (excluding folders and .delete)
                self.total_files = sum(1 for item in metadata[:-1] 
                                     if not item['path'].endswith('/') and item['path'] != '.delete')
            else:
                # For individual files
                self.total_files = len(metadata)
                
            self.file_count_update.emit(self.total_files, 0, self.total_files)
            
            return metadata
        except UnicodeDecodeError as e:
            logger.error("Unicode decode error: %s", e)
            raise
        except json.JSONDecodeError as e:
            logger.error("JSON decode error: %s", e)
            raise

    def create_folder_structure(self, metadata):
        """Create folder structure based on metadata."""
        # Get the default directory from configuration
        config = self.config_manager.get_config()
        default_dir = config["save_to_directory"]

        if not default_dir:
            raise ValueError("No save_to_directory configured")

        # Extract the base folder name from the last metadata entry
        top_level_folder = metadata[-1].get('base_folder_name', '')
        if not top_level_folder:
            raise ValueError("Base folder name not found in metadata")

        # Define the destination folder path and ensure it is unique
        destination_folder = os.path.join(default_dir, top_level_folder)
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

                # Ensure the folder is unique and not a duplicate
                if full_folder_path not in created_folders:
                    full_folder_path = self._get_unique_folder_name(full_folder_path)

                    # Create the directory if it does not exist
                    if not os.path.exists(full_folder_path):
                        os.makedirs(full_folder_path)
                        logger.debug("Created folder: %s", full_folder_path)

                    # Add the folder to the set of created folders
                    created_folders.add(full_folder_path)
                else:
                    logger.debug("Folder already exists: %s", full_folder_path)

        return destination_folder
    #com.an.Datadash

    def _get_unique_folder_name(self, folder_path):
        """Append a unique (i) to folder name if it already exists."""
        base_folder_path = folder_path
        i = 1
        # Check for existence and modify name with incrementing (i)
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
        config = self.config_manager.get_config()
        default_dir = config.get("save_to_directory")
        if not default_dir:
            raise NotImplementedError("Unsupported OS")
        return os.path.join(default_dir, file_name)

    def close_connection(self):
        """Safely close all network connections"""
        for sock in [self.client_skt, self.server_skt]:
            if sock:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except:
                    pass
                finally:
                    try:
                        sock.close()
                    except:
                        pass

        self.client_skt = None
        self.server_skt = None
        logger.debug("All connections closed")

    def stop(self):
        """Stop all operations and cleanup resources"""
        try:
            self.broadcasting = False
            self.close_connection()
            self.quit()
            self.wait(2000)  # Wait up to 2 seconds for thread to finish
            if self.isRunning():
                self.terminate()
        except Exception as e:
            logger.error(f"Error during worker stop: {e}")

class ReceiveAppP(QWidget):
    progress_update = pyqtSignal(int)

    def __init__(self, client_ip, sender_os):
        super().__init__()
        self.client_ip = client_ip
        self.sender_os = sender_os  # Store sender's OS
        self.initUI()
        self.setFixedSize(853, 480)
        #com.an.Datadash

        self.current_text = self.displaytxt()  # The full text for the label
        self.displayed_text = ""  # Text that will appear with typewriter effect
        self.char_index = 0  # Keeps track of the character index for typewriter effect
        self.progress_bar.setVisible(False)  # Initially hidden
        self.config_manager = ConfigManager()

        self.file_receiver = ReceiveWorkerPython(client_ip)
        self.file_receiver.progress_update.connect(self.updateProgressBar)
        self.file_receiver.file_progress_update.connect(self.update_file_progress)
        self.file_receiver.decrypt_signal.connect(self.decryptor_init)
        self.file_receiver.receiving_started.connect(self.show_progress_bar)
        self.file_receiver.transfer_finished.connect(self.onTransferFinished)
        self.file_receiver.update_files_table_signal.connect(self.update_files_table)
        self.file_name_map = {}  # Add dictionary to track renamed files
        self.file_receiver.file_renamed_signal.connect(self.handle_file_rename)
        # Connect the stats update signal
        self.file_receiver.transfer_stats_update.connect(self.update_transfer_stats)
        # Connect the file count update signal
        self.file_receiver.file_count_update.connect(self.updateFileCounts)

        # Start the typewriter effect
        self.typewriter_timer = QTimer(self)
        self.typewriter_timer.timeout.connect(self.update_typewriter_effect)
        self.typewriter_timer.start(50)  # Adjust speed of typewriter effect

        # Start the file receiving process directly on the main thread
        self.file_receiver.start()
        self.main_window = None

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
        #com.an.Datadash

        # Top section with animation and label
        top_layout = QHBoxLayout()
        
        self.loading_label = QLabel(self)
        self.loading_label.setStyleSheet("QLabel { background-color: transparent; border: none; }")
        self.receiving_movie = QMovie(receiving_gif_path)
        self.success_movie = QMovie(success_gif_path)
        self.receiving_movie.setScaledSize(QtCore.QSize(50, 50))  # Reduced size
        self.success_movie.setScaledSize(QtCore.QSize(50, 50))
        self.loading_label.setMovie(self.receiving_movie)
        self.receiving_movie.start()
        
        self.label = QLabel("", self)
        self.label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 24px;
                background: transparent;
                border: none;
                font-weight: bold;
            }
        """)
        
        top_layout.addWidget(self.loading_label)
        top_layout.addWidget(self.label)
        top_layout.addStretch()
        layout.addLayout(top_layout)

        # Files table
        self.files_table = QTableWidget()
        self.files_table.setMinimumHeight(200)  # Add minimum height
        self.files_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)  # Add size policy
        self.files_table.setColumnCount(4)
        self.files_table.setShowGrid(True)
        self.files_table.verticalHeader().setVisible(False)
        self.files_table.setHorizontalHeaderLabels(['Sr No.', 'File Name', 'Size', 'Progress'])
        self.files_table.setStyleSheet("""
            QTableWidget {
                background-color: #2f3642;
                color: white;
                border: 1px solid #4b5562;
                border-radius: 10px;
                gridline-color: #4b5562;
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #1f242d;
                color: white;
                padding: 8px;
                border: 1px solid #4b5562;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #4b5562;
            }
            QTableWidget::item:selected {
                background-color: #3d4452;
            }
        """)
        
        # Configure columns
        self.files_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.files_table.setColumnWidth(0, 60)
        
        # File Name column - expanding width
        self.files_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        # Size column - fixed width
        self.files_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.files_table.setColumnWidth(2, 100)
        
        # Progress column - fixed width
        self.files_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.files_table.setColumnWidth(3, 200)
        
        self.files_table.setItemDelegate(ProgressBarDelegate())
        layout.addWidget(self.files_table)

        # Add file counts label
        self.file_counts_label = QLabel("Total files: 0 | Completed: 0 | Pending: 0")
        self.file_counts_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 14px;
                background-color: transparent;
            }
        """)
        layout.addWidget(self.file_counts_label)

        # Overall progress bar at bottom
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

        # Add transfer stats label
        self.transfer_stats_label = QLabel()
        self.transfer_stats_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 12px;
                background: transparent;
                padding: 5px;
            }
        """)
        self.transfer_stats_label.setVisible(False)
        layout.addWidget(self.transfer_stats_label)

        # Buttons
        buttons_layout = QHBoxLayout()
        # Open directory button
        self.open_dir_button = self.create_styled_button('Open Receiving Directory')
        self.open_dir_button.clicked.connect(self.open_receiving_directory)
        self.open_dir_button.setVisible(False)  # Initially hidden
        buttons_layout.addWidget(self.open_dir_button)
        #com.an.Datadash

        # Keep them disabled until the file transfer is completed
        self.close_button = self.create_styled_button('Close')  # Apply styling here
        self.close_button.setVisible(False)
        self.close_button.clicked.connect(self.close)
        buttons_layout.addWidget(self.close_button)

        self.mainmenu_button = self.create_styled_button('Main Menu')
        self.mainmenu_button.setVisible(False)
        self.mainmenu_button.clicked.connect(self.openMainWindow)
        buttons_layout.addWidget(self.mainmenu_button)

        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.openMainWindow()

    def displaytxt(self):
        if self.sender_os == 'Windows':
            return 'Waiting to receive files from a Windows device'
        elif self.sender_os == 'Linux':
            return 'Waiting to receive files from a Linux device'
        elif self.sender_os == 'Darwin':
            return 'Waiting to receive files from a macOS device'
        else:
            return 'Waiting to receive files from Desktop app'

    def displaytxtreceive(self):
        if self.sender_os == 'Windows':
            return 'Receiving files from a Windows device'
        elif self.sender_os == 'Linux':
            return 'Receiving files from a Linux device'
        elif self.sender_os == 'Darwin':
            return 'Receiving files from a macOS device'
        else:
            return 'Receiving files from Desktop app'

    def openMainWindow(self):
        from main import MainApp
        self.main_window = MainApp()
        self.main_window.show()
        self.close()

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
        self.label.setText(self.displaytxtreceive())

    def update_typewriter_effect(self):
        """Updates the label text one character at a time."""
        if self.char_index < len(self.current_text):
            self.displayed_text += self.current_text[self.char_index]
            self.label.setText(self.displayed_text)
            self.char_index += 1
        else:
            # Stop the timer when the entire text is displayed
            self.typewriter_timer.stop()
            #com.an.Datadash

    def updateProgressBar(self, value):
        self.progress_bar.setValue(value)

    def update_files_table(self, metadata):
        """Update table with files from metadata"""
        try:
            # Clear existing rows
            self.files_table.setRowCount(0)
            
            if self.file_receiver.folder_transfer:
                # For folder transfer, only show the folder
                folder_name = metadata[0].get('base_folder_name', '')  # Changed from [-1] to [0]
                if folder_name:
                    # Explicitly insert a new row first
                    self.files_table.insertRow(0)
                    
                    # Add serial number with center alignment
                    sr_item = QTableWidgetItem('1')
                    sr_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.files_table.setItem(0, 0, sr_item)
                    
                    # Folder name
                    name_item = QTableWidgetItem(folder_name)
                    name_item.setToolTip("Folder transfer")
                    self.files_table.setItem(0, 1, name_item)
                    
                    # Total size calculation from the original metadata in file_receiver
                    total_size = sum(file_info.get('size', 0) for file_info in self.file_receiver.metadata[:-1]
                                   if file_info.get('path') != '.delete')
                    
                    # Size formatting
                    if total_size >= 1024 * 1024:  # MB
                        size_str = f"{total_size / (1024 * 1024):.2f} MB"
                    elif total_size >= 1024:  # KB 
                        size_str = f"{total_size / 1024:.2f} KB"
                    else:  # Bytes
                        size_str = f"{total_size} B"
                    self.files_table.setItem(0, 2, QTableWidgetItem(size_str))
                    
                    # Progress (initially 0)
                    progress_item = QTableWidgetItem()
                    progress_item.setData(Qt.ItemDataRole.UserRole, 0)
                    self.files_table.setItem(0, 3, progress_item)
                    
                    logger.debug(f"Added folder to table: {folder_name}")
            else:
                # Original file-by-file display logic
                for index, file_info in enumerate(metadata, start=1):
                    if file_info.get('path') == '.delete' or 'base_folder_name' in file_info:
                        continue
                    
                    file_path = file_info.get('path', '')
                    if not file_path:
                        continue

                    # Insert new row and get its index
                    row = self.files_table.rowCount()
                    self.files_table.insertRow(row)
                    
                    try:
                        # Add serial number with center alignment
                        sr_item = QTableWidgetItem(str(index))
                        sr_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        self.files_table.setItem(row, 0, sr_item)
                        
                        # File name
                        name_item = QTableWidgetItem(os.path.basename(file_path))
                        name_item.setToolTip(file_path)
                        self.files_table.setItem(row, 1, name_item)
                        
                        # Size
                        size = file_info.get('size', 0)
                        if size >= 1024 * 1024:  # MB
                            size_str = f"{size / (1024 * 1024):.2f} MB"
                        elif size >= 1024:  # KB 
                            size_str = f"{size / 1024:.2f} KB"
                        else:  # Bytes
                            size_str = f"{size} B"
                        self.files_table.setItem(row, 2, QTableWidgetItem(size_str))
                        
                        # Progress (initially 0)
                        progress_item = QTableWidgetItem()
                        progress_item.setData(Qt.ItemDataRole.UserRole, 0)
                        self.files_table.setItem(row, 3, progress_item)
                        
                        # Log successful file entry
                        logger.debug(f"Added file to table: {file_path}")
                        
                    except Exception as e:
                        logger.error(f"Error adding file to table: {file_path}, Error: {str(e)}")
                        # Remove the problematic row if there was an error
                        self.files_table.removeRow(row)

        except Exception as e:
            logger.error(f"Error updating files table: {str(e)}")

    def handle_file_rename(self, old_name, new_name):
        """Track renamed files - now handles both encrypted and unencrypted files"""
        self.file_name_map[old_name] = new_name
        # Update the table with the new filename (without .crypt extension for encrypted files)
        for row in range(self.files_table.rowCount()):
            if self.files_table.item(row, 1).text() == os.path.basename(old_name):
                display_name = os.path.basename(new_name)
                if display_name.endswith('.crypt'):
                    display_name = display_name[:-6]  # Remove .crypt extension for display
                self.files_table.item(row, 1).setText(display_name)
                self.files_table.item(row, 1).setToolTip(new_name)
                break

    def update_file_progress(self, file_name, progress):
        """Update progress for a specific file or folder."""
        if self.file_receiver.folder_transfer:
            if file_name == "folder_progress":  # Special case for folder progress
                progress_item = QTableWidgetItem()
                progress_item.setData(Qt.ItemDataRole.UserRole, progress)
                self.files_table.setItem(0, 3, progress_item)
        else:
            # Check if the file was renamed
            actual_name = self.file_name_map.get(file_name, file_name)
            
            # Look for the file in the table - compare without .crypt extension
            for row in range(self.files_table.rowCount()):
                table_filename = self.files_table.item(row, 1).text()
                compare_name = os.path.basename(actual_name)
                if compare_name.endswith('.crypt'):
                    compare_name = compare_name[:-6]
                if table_filename == os.path.basename(compare_name):
                    progress_item = QTableWidgetItem()
                    progress_item.setData(Qt.ItemDataRole.UserRole, progress)
                    self.files_table.setItem(row, 3, progress_item)
                    break

    def update_transfer_stats(self, speed, eta, elapsed):
        """Update the transfer statistics label"""
        if not self.transfer_stats_label.isVisible():
            self.transfer_stats_label.setVisible(True)
            
        eta_str = time.strftime("%H:%M:%S", time.gmtime(eta))
        elapsed_str = time.strftime("%H:%M:%S", time.gmtime(elapsed))
        stats_text = f"Speed: {speed:.2f} MB/s | ETA: {eta_str} | Elapsed: {elapsed_str}"
        self.transfer_stats_label.setText(stats_text)

    def updateFileCounts(self, total_files, files_received, files_pending):
        """Update the file counts label with current transfer progress"""
        self.file_counts_label.setText(
            f"Total files: {total_files} | Completed: {files_received} | Pending: {files_pending}"
        )

    def onTransferFinished(self):
        # Adjust the top section to be more compact
        self.receiving_movie.stop()
        self.loading_label.setMovie(self.success_movie)
        self.success_movie.start()
        self.label.setText("Transfer completed successfully!")
        
        self.open_dir_button.setVisible(True)
        self.close_button.setVisible(True)
        self.mainmenu_button.setVisible(True)

    def decryptor_init(self, value):
        logger.debug("Received decrypt signal with filelist %s", value)
        if value:
            self.decryptor = Decryptor(value)
            self.decryptor.show()

    def open_receiving_directory(self):
        config = self.file_receiver.config_manager.get_config()
        receiving_dir = config.get("save_to_directory", "")

        if receiving_dir:
            try:
                current_os = platform.system()

                if current_os == 'Windows':
                    os.startfile(receiving_dir)

                elif current_os == 'Linux':
                    file_managers = [
                        # ["xdg-open", receiving_dir],
                        # ["xdg-mime", "open", receiving_dir],
                        ["dbus-send", "--print-reply", "--dest=org.freedesktop.FileManager1",
                         "/org/freedesktop/FileManager1", "org.freedesktop.FileManager1.ShowFolders",
                         "array:string:" +"file://"+ receiving_dir, "string:"]
                        
                        # ["gio", "open", receiving_dir],
                        # ["gvfs-open", receiving_dir],
                        # ["kde-open", receiving_dir],
                        # ["kfmclient", "exec", receiving_dir],
                        # ["nautilus", receiving_dir],
                        # ["dolphin", receiving_dir],
                        # ["thunar", receiving_dir],
                        # ["pcmanfm", receiving_dir],
                        # ["krusader", receiving_dir],
                        # ["mc", receiving_dir],
                        # ["nemo", receiving_dir],
                        # ["caja", receiving_dir],
                        # ["konqueror", receiving_dir],
                        # ["gwenview", receiving_dir],
                        # ["gimp", receiving_dir],
                        # ["eog", receiving_dir],
                        # ["feh", receiving_dir],
                        # ["gpicview", receiving_dir],
                        # ["mirage", receiving_dir],
                        # ["ristretto", receiving_dir],
                        # ["viewnior", receiving_dir],
                        # ["gthumb", receiving_dir],
                        # ["nomacs", receiving_dir],
                        # ["geeqie", receiving_dir],
                        # ["gwenview", receiving_dir],
                        # ["gpicview", receiving_dir],
                        # ["mirage", receiving_dir],
                        # ["ristretto", receiving_dir],
                        # ["viewnior", receiving_dir],
                        # ["gthumb", receiving_dir],
                        # ["nomacs", receiving_dir],
                        # ["geeqie", receiving_dir],
                    ]

                    success = False
                    for cmd in file_managers:
                        try:
                            subprocess.run(cmd, timeout=3, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                            logger.info(f"Successfully opened directory with {cmd[0]}")
                            success = True
                            break
                        except subprocess.TimeoutExpired:
                            continue
                        except FileNotFoundError:
                            continue
                        except Exception as e:
                            logger.debug(f"Failed to open with {cmd[0]}: {str(e)}")
                            continue

                    if not success:
                        raise Exception("No suitable file manager found")

                elif current_os == 'Darwin':  # macOS
                    subprocess.Popen(["open", receiving_dir])

                else:
                    raise NotImplementedError(f"Unsupported OS: {current_os}")

            except FileNotFoundError as fnfe:
                logger.error("No file manager found: %s", fnfe)
            except Exception as e:
                logger.error("Failed to open directory: %s", str(e))
        else:
            logger.error("No receiving directory configured.")

    def show_error_message(self, title, message, detailed_text):
        QMessageBox.critical(self, title, message)

    def cleanup(self):
        logger.info("Cleaning up ReceiveAppP resources")
        
        # Stop typewriter effect
        if hasattr(self, 'typewriter_timer'):
            self.typewriter_timer.stop()
            
        # Stop file receiver and cleanup
        if hasattr(self, 'file_receiver'):
            self.file_receiver.stop()
            self.file_receiver.close_connection()
            
            # Ensure thread is properly terminated
            if not self.file_receiver.wait(3000):  # Wait up to 3 seconds
                self.file_receiver.terminate()
                self.file_receiver.wait()
            
        # Stop any running movies
        if hasattr(self, 'receiving_movie'):
            self.receiving_movie.stop()
        if hasattr(self, 'success_movie'):
            self.success_movie.stop()

        # Close main window if it exists
        if self.main_window:
            self.main_window.close()

    def closeEvent(self, event):
        logger.info("Shutting down ReceiveAppP")
        self.cleanup()
        QApplication.quit()
        event.accept()

    def closeEvent(self, event):
        """Handle application close event"""
        try:
            # Stop the typewriter effect
            if hasattr(self, 'typewriter_timer'):
                self.typewriter_timer.stop()

            # Stop file receiver and cleanup
            if hasattr(self, 'file_receiver'):
                self.file_receiver.stop()
                self.file_receiver.close_connection()

                # Ensure thread is properly terminated
                if not self.file_receiver.wait(3000):  # Wait up to 3 seconds
                    self.file_receiver.terminate()
                    self.file_receiver.wait()

            # Stop any running movies
            if hasattr(self, 'receiving_movie'):
                self.receiving_movie.stop()
            if hasattr(self, 'success_movie'):
                self.success_movie.stop()

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        finally:
            event.accept()

    def __del__(self):
        """Ensure cleanup on object destruction"""
        try:
            if hasattr(self, 'file_receiver'):
                self.file_receiver.stop()
                self.file_receiver.close_connection()
            if hasattr(self, 'config_manager'):
                self.config_manager.quit()
                self.config_manager.wait()        
        except:
            pass

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    receive_app = ReceiveAppP("127.0.0.1",  None)
    receive_app.show()
    app.exec()
    #com.an.Datadash