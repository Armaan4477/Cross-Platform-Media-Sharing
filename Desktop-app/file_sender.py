import json
import platform
import tempfile
from pathlib import Path
from PyQt6.QtWidgets import (
    QMessageBox, QWidget, QVBoxLayout, QPushButton, QListWidget, 
    QProgressBar, QLabel, QFileDialog, QApplication, QListWidgetItem, QTextEdit, QLineEdit, QSizePolicy,
    QHBoxLayout, QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QStyledItemDelegate, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QScreen, QFont, QColor, QKeyEvent, QKeySequence, QIcon
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QElapsedTimer, QTimer, QSize
import os
import socket
import struct
from constant import ConfigManager  # Updated import
from loges import logger
from crypt_handler import encrypt_file
from time import sleep
from portsss import RECEIVER_DATA_DESKTOP, CHUNK_SIZE_DESKTOP
import time

class ProgressBarDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        if index.column() == 3:  # Progress column (changed from 2 to 3)
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

class FileSender(QThread):
    progress_update = pyqtSignal(int)
    file_send_completed = pyqtSignal(str)
    transfer_finished = pyqtSignal()
    file_count_update = pyqtSignal(int, int, int)  # total_files, files_sent, files_pending
    file_progress_update = pyqtSignal(str, int)  # file_path, progress
    overall_progress_update = pyqtSignal(int)  # overall progress
    transfer_stats_update = pyqtSignal(float, float, float)  # speed, eta, elapsed

    password = None

    def __init__(self, ip_address, file_paths, password=None, receiver_data=None):
        super().__init__()
        self.config_manager = ConfigManager()
        self.config_manager.start()
        self.ip_address = ip_address
        self.file_paths = file_paths
        self.password = password
        self.receiver_data = receiver_data
        self.total_files = self.count_total_files()
        self.files_sent = 0
        self.total_size = self.calculate_total_size()
        self.sent_size = 0
        self.start_time = None
        self.last_update_time = None
        self.last_bytes_sent = 0

    def count_total_files(self):
        total = 0
        for path in self.file_paths:
            if os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    total += len(files)
            else:
                total += 1
        return total

    def calculate_total_size(self):
        total_size = 0
        for path in self.file_paths:
            if os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    for file in files:
                        total_size += os.path.getsize(os.path.join(root, file))
            else:
                total_size += os.path.getsize(path)
        return total_size

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
            self.client_skt.connect((self.ip_address, RECEIVER_DATA_DESKTOP))  # Connect to receiver's IP and port
            logger.debug(f"Successfully connected to {self.ip_address} on port {RECEIVER_DATA_DESKTOP}")
        except ConnectionRefusedError:
            logger.error("Connection refused: Failed to connect to the specified IP address.")
            self.show_message_box("Connection Error", "Failed to connect to the specified IP address.")
            return False
        except OSError as e:
            logger.error(f"Binding error: {e}")
            self.show_message_box("Binding Error", f"Failed to bind to the specified port: {e}")
            return False

        return True

    def show_message_box(self, title, message):
        msg_box = QMessageBox()
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()

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
        
        self.encryption_flag = self.config_manager.get_config()["encryption"]

        for file_path in self.file_paths:
            if os.path.isdir(file_path):
                self.send_folder(file_path)
            else:
                if not self.metadata_created:
                    metadata_file_path = self.create_metadata(file_paths=self.file_paths)
                    self.send_file(metadata_file_path, count=False)
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
                    relative_path = os.path.relpath(file_path, folder_path).replace('\\', '/')
                    file_size = os.path.getsize(file_path)
                    metadata.append({
                        'path': relative_path,
                        'size': file_size
                    })
                for dir in dirs:
                    dir_path = os.path.join(root, dir)
                    relative_path = os.path.relpath(dir_path, folder_path).replace('\\', '/')
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
        try:
            if not self.metadata_created:
                # Create and send metadata first
                metadata_file_path = self.create_metadata(folder_path=folder_path)
                with open(metadata_file_path, 'rb') as f:
                    metadata_content = f.read()
                
                # Send metadata file with proper headers
                encryption_flag = 'encyp: f'
                file_name = 'metadata.json'
                file_name_size = len(file_name.encode())
                file_size = len(metadata_content)

                # Send headers
                self.client_skt.send(encryption_flag.encode())
                self.client_skt.send(struct.pack('<Q', file_name_size))
                self.client_skt.send(file_name.encode('utf-8'))
                self.client_skt.send(struct.pack('<Q', file_size))

                # Send metadata content in chunks
                sent = 0
                while sent < file_size:
                    chunk = metadata_content[sent:sent + CHUNK_SIZE_DESKTOP]
                    self.client_skt.send(chunk)
                    sent += len(chunk)

                # Read metadata for processing
                metadata = json.loads(open(metadata_file_path).read())

                # Calculate total folder size and prepare files
                folder_total_size = sum(file_info['size'] for file_info in metadata 
                                     if not file_info['path'].endswith('.delete') and file_info['size'] > 0)
                folder_sent_size = 0

                # Send each file
                for file_info in metadata:
                    if not file_info['path'].endswith('.delete') and file_info['size'] > 0:
                        relative_file_path = file_info['path']
                        file_path = os.path.join(folder_path, relative_file_path)
                        if self.encryption_flag:
                            relative_file_path += ".crypt"
                        
                        # Send the actual file
                        if os.path.exists(file_path):
                            self.send_file(file_path, relative_file_path=relative_file_path, 
                                         encrypted_transfer=self.encryption_flag)
                            folder_sent_size += file_info['size']
                            folder_progress = folder_sent_size * 100 // folder_total_size
                            self.file_progress_update.emit(folder_path, folder_progress)

                os.remove(metadata_file_path)

        except Exception as e:
            logger.error(f"Error in send_folder: {str(e)}")
            raise

    def send_file(self, file_path, relative_file_path=None, encrypted_transfer=False, count=True):
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

        if not self.start_time:
            self.start_time = time.time()
        self.last_update_time = time.time()

        with open(file_path, 'rb') as f:
            while sent_size < file_size:
                current_time = time.time()
                data = f.read(CHUNK_SIZE_DESKTOP)
                self.client_skt.sendall(data)
                sent_size += len(data)
                self.sent_size += len(data)
                
                # Calculate transfer statistics every 0.5 seconds
                if current_time - self.last_update_time >= 0.5:
                    elapsed = current_time - self.start_time
                    speed = (self.sent_size - self.last_bytes_sent) / (current_time - self.last_update_time) / (1024 * 1024)  # MB/s
                    remaining_bytes = self.total_size - self.sent_size
                    eta = remaining_bytes / (speed * 1024 * 1024) if speed > 0 else 0
                    
                    self.transfer_stats_update.emit(speed, eta, elapsed)
                    self.last_update_time = current_time
                    self.last_bytes_sent = self.sent_size

                self.file_progress_update.emit(file_path, sent_size * 100 // file_size)
                overall_progress = self.sent_size * 100 // self.total_size
                self.overall_progress_update.emit(overall_progress)

        if count:
            self.files_sent += 1
            files_pending = self.total_files - self.files_sent
            self.file_count_update.emit(self.total_files, self.files_sent, files_pending)

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
        self.config_manager = ConfigManager()
        self.config_manager.config_updated.connect(self.on_config_updated)
        self.config_manager.log_message.connect(logger.info)
        self.config_manager.start()
        self.ip_address = ip_address
        self.device_name = device_name
        self.receiver_data = receiver_data
        self.file_paths = []
        self.file_progress_bars = {}  # Initialize the dictionary for progress bars
        self.send_button = None  # Initialize the send button reference
        self.encryption_enabled = self.config_manager.get_config()["encryption"]
        self.file_name_map = {}  # Add mapping for encrypted files
        self.initUI()
        self.progress_bar.setVisible(False)
        self.main_window = None
        self.file_sender = None

    def cleanup(self):
        logger.info("Cleaning up SendApp resources")
        
        # Stop file sender thread
        if self.file_sender and self.file_sender.isRunning():
            self.file_sender.stop()
            self.file_sender.wait()

        # Close main window if it exists
        if self.main_window:
            self.main_window.close()

        # Close any open sockets
        if hasattr(self, 'client_skt'):
            try:
                self.client_skt.close()
            except:
                pass

    def closeEvent(self, event):
        logger.info("Shutting down SendApp")
        self.cleanup()
        QApplication.quit()
        event.accept()

    def on_config_updated(self, config):
        self.current_config = config
    
    def add_file_to_table(self, file_path):
     row_position = self.file_table.rowCount()
     self.file_table.insertRow(row_position)

     # Remove button (Column 0)
     remove_button = QPushButton("X")
     remove_button.setStyleSheet("""
         QPushButton {
             background-color: #ff4d4d;
             color: white;
             border: none;
             padding: 2px 5px;
             border-radius: 2px;
             margin: 2px;
             max-width: 50px;
         }
         QPushButton:hover {
             background-color: #ff1a1a;
         }
         QPushButton:pressed {
            background-color: #cc0000;
        }
     """)
     remove_button.clicked.connect(lambda checked, fp=file_path: self.remove_file(fp))
    
     button_widget = QWidget()
     button_widget.setStyleSheet("background: transparent;")
     button_layout = QHBoxLayout(button_widget)
     button_layout.addWidget(remove_button)
     button_layout.setContentsMargins(2, 2, 2, 2)
     button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
     self.file_table.setCellWidget(row_position, 0, button_widget)

     # File name (Column 1)
     if os.path.isdir(file_path):
        folder_name = os.path.basename(file_path)
        name_item = QTableWidgetItem(folder_name)
        name_item.setFlags(name_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
        name_item.setToolTip(file_path)
        self.file_table.setItem(row_position, 1, name_item)

        total_size = self.get_folder_size(file_path)
        file_count = sum([len(files) for _, _, files in os.walk(file_path)])
        size_str = self.format_size(total_size, file_count)
     else:
        name_item = QTableWidgetItem(os.path.basename(file_path))
        name_item.setFlags(name_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
        name_item.setToolTip(file_path)
        self.file_table.setItem(row_position, 1, name_item)

        total_size = os.path.getsize(file_path)
        size_str = self.format_size(total_size)

     # Size (Column 2)
     size_item = QTableWidgetItem(size_str)
     size_item.setFlags(size_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
     self.file_table.setItem(row_position, 2, size_item)

     # Progress (Column 3) 
     progress_item = QTableWidgetItem()
     progress_item.setData(Qt.ItemDataRole.UserRole, 0)
     self.file_table.setItem(row_position, 3, progress_item)
     self.file_progress_bars[file_path] = progress_item

    def remove_file(self, file_path):
     for row in range(self.file_table.rowCount()):
        name_item = self.file_table.item(row, 1)
        if name_item and name_item.toolTip() == file_path:
            self.file_table.removeRow(row)
            if file_path in self.file_paths:
                self.file_paths.remove(file_path)
            if file_path in self.file_progress_bars:
                del self.file_progress_bars[file_path]
            break
    
     if self.file_table.rowCount() == 0:
        self.send_button.setVisible(False)
     self.checkReadyToSend()

    def create_styled_button(self, text, with_radius=True):
        """Enhanced button styling with optional radius and improved visuals"""
        button = QPushButton(text)
        radius = "25px" if with_radius else "8px"
        button.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        button.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(47, 54, 66, 255),
                    stop: 1 rgba(75, 85, 98, 255)
                );
                color: white;
                border-radius: {radius};
                border: 1px solid rgba(0, 0, 0, 0.5);
                padding: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(60, 68, 80, 255),
                    stop: 1 rgba(90, 100, 118, 255)
                );
            }}
            QPushButton:pressed {{
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(35, 41, 51, 255),
                    stop: 1 rgba(65, 75, 88, 255)
                );
            }}
            QPushButton:disabled {{
                background: #666;
                color: #aaa;
            }}
        """)
        
        # Add glow effect
        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(15)
        glow.setXOffset(0)
        glow.setYOffset(0)
        glow.setColor(QColor(255, 255, 255, 100))
        button.setGraphicsEffect(glow)
        
        return button

    def initUI(self):
        logger.debug("Encryption : %s", self.config_manager.get_config()["encryption"])
        self.setWindowTitle('DataDash: Send File')
        self.setFixedSize(853, 480)
        self.center_window()

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Top section with title
        top_layout = QHBoxLayout()
        
        title_label = QLabel("DataDash: Send File")
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 24px;
                background: transparent;
                border: none;
                font-weight: bold;
            }
        """)
        top_layout.addWidget(title_label)
        top_layout.addStretch()
        main_layout.addLayout(top_layout)

        # File selection buttons in horizontal layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)  # More space between buttons
        
        # Select Files button with correct icon
        self.file_button = self.create_styled_button('Select Files')
        self.file_button.setFixedSize(150, 50)
        self.file_button.setIcon(QIcon(os.path.join(os.path.dirname(__file__), "icons", "Files.svg")))  # Changed from file.svg
        self.file_button.setIconSize(QSize(24, 24))
        self.file_button.clicked.connect(self.selectFile)
        
        # Select Folder button with correct icon
        self.folder_button = self.create_styled_button('Select Folder')
        self.folder_button.setFixedSize(150, 50)
        self.folder_button.setIcon(QIcon(os.path.join(os.path.dirname(__file__), "icons", "Folders.svg")))  # Changed from folder.svg
        self.folder_button.setIconSize(QSize(24, 24))
        self.folder_button.clicked.connect(self.selectFolder)
        
        button_layout.addWidget(self.file_button)
        button_layout.addWidget(self.folder_button)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        # Files table - Fixed height and stretch
        self.file_table = QTableWidget()
        self.file_table.setMinimumHeight(200)  # Add minimum height
        self.file_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)  # Add size policy
        self.file_table.setColumnCount(4)
        self.file_table.setHorizontalHeaderLabels(['Remove', 'File Name', 'Size', 'Progress'])
        self.file_table.setStyleSheet("""
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
        self.file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.file_table.setColumnWidth(0, 60)  # Remove button column
        self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Filename column
        self.file_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.file_table.setColumnWidth(2, 100)  # Size column
        self.file_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.file_table.setColumnWidth(3, 200)  # Progress column
        self.file_table.setItemDelegate(ProgressBarDelegate())
        main_layout.addWidget(self.file_table)

                
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
        main_layout.addWidget(self.transfer_stats_label)

        # File counts label
        self.file_counts_label = QLabel("Total files: 0 | Completed: 0 | Pending: 0")
        self.file_counts_label.setStyleSheet("color: white; font-size: 14px; background-color: transparent;")
        main_layout.addWidget(self.file_counts_label)

        # Password input (if encryption is enabled)
        if self.encryption_enabled:
            password_layout = QHBoxLayout()
            password_layout.setSpacing(10)
            
            self.password_label = QLabel('🔒 Encryption Password:')
            self.password_label.setStyleSheet("""
                color: white;
                font-size: 14px;
                font-weight: bold;
                background-color: transparent;
            """)
            
            self.password_input = QLineEdit()
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.password_input.setStyleSheet("""
                QLineEdit {
                    background-color: #2f3642;
                    color: white;
                    border: 2px solid #4b5562;
                    border-radius: 8px;
                    padding: 8px;
                    font-size: 14px;
                }
                QLineEdit:focus {
                    border: 2px solid #6c7989;
                }
            """)
            self.password_input.setFixedHeight(35)
            
            password_layout.addWidget(self.password_label)
            password_layout.addWidget(self.password_input)
            main_layout.addLayout(password_layout)

        # Overall progress bar
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
        main_layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 18px;
                font-weight: bold;
                background-color: transparent;
                padding: 10px;
            }
        """)
        main_layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Bottom buttons layout
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(15)
        
        # Send button with same style as main menu
        self.send_button = self.create_styled_button('Send')  # Changed text to match main menu style
        self.send_button.setFixedSize(150, 50)
        self.send_button.setIcon(QIcon(os.path.join(os.path.dirname(__file__), "icons", "send.svg")))
        self.send_button.setIconSize(QSize(24, 24))
        self.send_button.clicked.connect(self.sendSelectedFiles)  # Add this line to connect the click signal
        self.send_button.setVisible(False)
        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(15)
        glow.setXOffset(0)
        glow.setYOffset(0)
        glow.setColor(QColor(255, 255, 255, 100))
        self.send_button.setGraphicsEffect(glow)
        
        self.close_button = self.create_styled_button('Close', with_radius=False)
        self.close_button.setFixedSize(120, 35)
        self.close_button.setVisible(False)
        self.close_button.clicked.connect(self.close)
        
        self.mainmenu_button = self.create_styled_button('Main Menu', with_radius=False)
        self.mainmenu_button.setFixedSize(120, 35)
        self.mainmenu_button.setVisible(False)
        self.mainmenu_button.clicked.connect(self.openMainWindow)
        
        # Center the buttons
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.send_button)
        buttons_layout.addWidget(self.close_button)
        buttons_layout.addWidget(self.mainmenu_button)
        buttons_layout.addStretch()
        
        main_layout.addLayout(buttons_layout)
        
        self.setLayout(main_layout)
        self.set_background()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.openMainWindow()

    def openMainWindow(self):
        from main import MainApp
        self.main_window = MainApp()
        self.main_window.show()
        self.close()

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
            self.file_table.setRowCount(0)
            for file_path in file_paths:
                self.add_file_to_table(file_path)
            self.file_paths = file_paths
            self.checkReadyToSend()

    def selectFolder(self):
        documents= self.get_default_path()
        folder_path = QFileDialog.getExistingDirectory(self, 'Select Folder', documents)
        if folder_path:
            self.file_table.setRowCount(0)
            self.add_file_to_table(folder_path)
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

    def get_folder_size(self, folder_path):
        """Calculate total size of a folder"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(folder_path):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                if os.path.exists(file_path):
                    total_size += os.path.getsize(file_path)
        return total_size
    
    def format_size(self, total_size, file_count=None):
        """Format size string with file count"""
        if total_size >= 1024 * 1024 * 1024:  # GB
            size_str = f"{total_size / (1024 * 1024 * 1024):.2f} GB"
        elif total_size >= 1024 * 1024:  # MB
            size_str = f"{total_size / (1024 * 1024):.2f} MB"
        elif total_size >= 1024:  # KB
            size_str = f"{total_size / 1024:.2f} KB"
        else:  # Bytes
            size_str = f"{total_size} B"
            
        if file_count is not None:
            size_str += f" ({file_count} items)"
        return size_str
    
    

    def sendSelectedFiles(self):
        password = None

        if self.config_manager.get_config()["encryption"]:
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
        self.file_sender.file_send_completed.connect(self.fileSent)
        self.file_sender.transfer_finished.connect(self.onTransferFinished)
        self.file_sender.file_count_update.connect(self.updateFileCounts)
        self.file_sender.file_progress_update.connect(self.updateFileProgressBar)
        self.file_sender.overall_progress_update.connect(self.updateOverallProgressBar)
        self.file_sender.transfer_stats_update.connect(self.updateTransferStats)
        self.file_sender.start()
        #com.an.Datadash

    def updateProgressBar(self, value):
        self.progress_bar.setValue(value)

    def fileSent(self, file_path):
        self.status_label.setText(f"File sent: {file_path}")

    def updateFileCounts(self, total_files, files_sent, files_pending):
        self.file_counts_label.setText(f"Total files: {total_files} | Completed: {files_sent} | Pending: {files_pending}")

    def updateFileProgressBar(self, file_path, value):
        if self.encryption_enabled and not file_path.endswith('metadata.json'):
            # Map the encrypted file path back to original file path
            original_path = file_path[:-6] if file_path.endswith('.crypt') else file_path
            
            # For folder progress updates
            if os.path.isdir(original_path):
                if original_path in self.file_progress_bars:
                    self.file_progress_bars[original_path].setData(Qt.ItemDataRole.UserRole, value)
                return

            # For individual files
            if original_path not in self.file_progress_bars:
                if original_path in self.file_paths:
                    self.add_file_to_table(original_path)
            
            if original_path in self.file_progress_bars:
                self.file_progress_bars[original_path].setData(Qt.ItemDataRole.UserRole, value)
        else:
            # Original non-encrypted logic
            if file_path not in self.file_progress_bars:
                if os.path.isdir(file_path) or file_path in self.file_paths:
                    self.add_file_to_table(file_path)
            if file_path in self.file_progress_bars:
                self.file_progress_bars[file_path].setData(Qt.ItemDataRole.UserRole, value)

    def updateOverallProgressBar(self, value):
        self.progress_bar.setValue(value)

    def updateTransferStats(self, speed, eta, elapsed):
        self.transfer_stats_label.setText(f"Speed: {speed:.2f} MB/s | ETA: {eta:.2f} s | Elapsed: {elapsed:.2f} s")
        self.transfer_stats_label.setVisible(True)

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
