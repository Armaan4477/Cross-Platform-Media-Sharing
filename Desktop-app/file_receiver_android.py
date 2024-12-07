import os
import socket
import struct
import json
from PyQt6 import QtCore
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QMetaObject,QTimer
from PyQt6.QtWidgets import QMessageBox, QWidget, QVBoxLayout, QLabel, QProgressBar, QApplication,QPushButton,QHBoxLayout
from PyQt6.QtGui import QScreen,QMovie,QFont,QKeySequence,QKeyEvent
from constant import get_config, logger
from crypt_handler import decrypt_file, Decryptor
import subprocess
import platform
import time
import shutil

RECEIVER_DATA = 57341

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
        self.base_folder_name = ''
        logger.debug(f"Client IP address stored: {self.store_client_ip}")

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
            self.server_skt.bind(('', RECEIVER_DATA))
            self.server_skt.listen(1)
            logger.debug("Server initialized on port %d", RECEIVER_DATA)
            
        except OSError as e:
            if e.errno == 48:  # Address already in use
                logger.error("Port %d is in use, waiting to retry...", RECEIVER_DATA)
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
            #com.an.Datadash
        else:
            logger.error("Failed to establish a connection.")

        # Close all active sockets
        if self.client_skt:
            self.client_skt.close()
        if self.server_skt:
            self.server_skt.close()


    def receive_files(self):
        self.broadcasting = False
        logger.debug("File reception started.")
        is_folder_transfer = False

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
                file_name = file_name.replace('\\', '/')
                logger.debug("Original file name: %s", file_name)

                # Receive file size
                file_size_data = self.client_skt.recv(8)
                file_size = struct.unpack('<Q', file_size_data)[0]

                try:
                    # Handle metadata.json
                    if file_name == 'metadata.json':
                        logger.debug("Receiving metadata file.")
                        self.metadata = self.receive_metadata(file_size)
                        
                        # Check if this is a folder transfer
                        is_folder_transfer = any(file_info.get('path', '').endswith('/') 
                                            for file_info in self.metadata)
                        
                        if is_folder_transfer:
                            self.destination_folder = self.create_folder_structure(self.metadata)
                        else:
                            # For single files, use default directory
                            self.destination_folder = get_config()["save_to_directory"]
                        continue

                    # Determine file path based on transfer type
                    if is_folder_transfer and self.metadata:
                        # Handle folder structure
                        relative_file_path = file_name
                        if self.base_folder_name and relative_file_path.startswith(self.base_folder_name + '/'):
                            relative_file_path = relative_file_path[len(self.base_folder_name) + 1:]
                        full_file_path = os.path.join(self.destination_folder, relative_file_path)
                    else:
                        # Handle single file
                        full_file_path = os.path.join(self.destination_folder, os.path.basename(file_name))

                    # Ensure directory exists and handle duplicates
                    os.makedirs(os.path.dirname(full_file_path), exist_ok=True)
                    full_file_path = self._get_unique_file_name(full_file_path)
                    logger.debug(f"Saving file to: {full_file_path}")

                    # Receive file data
                    with open(full_file_path, "wb") as f:
                        received_size = 0
                        remaining = file_size
                        while remaining > 0:
                            chunk_size = min(4096, remaining)
                            data = self.client_skt.recv(chunk_size)
                            if not data:
                                raise ConnectionError("Connection lost during file reception.")
                            f.write(data)
                            received_size += len(data)
                            remaining -= len(data)
                            progress = int(received_size * 100 / file_size)
                            self.progress_update.emit(progress)

                    if encrypted_transfer:
                        self.encrypted_files.append(full_file_path)

                except Exception as e:
                    logger.error(f"Error saving file {file_name}: {str(e)}")

            except Exception as e:
                logger.error("Error during file reception: %s", str(e))
                break

        self.broadcasting = True
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
        default_dir = get_config()["save_to_directory"]
        
        if not default_dir:
            raise ValueError("No save_to_directory configured")
        
        # Extract base folder name from paths
        base_folder_name = None
        for file_info in metadata:
            path = file_info.get('path', '')
            if path.endswith('/'):
                base_folder_name = path.rstrip('/').split('/')[0]
                logger.debug("Found base folder name: %s", base_folder_name)
                break

        # If base folder name not found, use the last entry
        if not base_folder_name:
            base_folder_name = metadata[-1].get('base_folder_name', '')
            logger.debug("Base folder name from last metadata entry: %s", base_folder_name)

        if not base_folder_name:
            raise ValueError("Base folder name not found in metadata")
        
        # Handle duplicate root folder name
        destination_folder = os.path.join(default_dir, base_folder_name)
        destination_folder = self._get_unique_folder_name(destination_folder)
        logger.debug("Destination folder: %s", destination_folder)
        
        # Create the root folder if it does not exist
        if not os.path.exists(destination_folder):
            os.makedirs(destination_folder)
            logger.debug("Created root folder: %s", destination_folder)
        
        # Store base folder name for use in receive_files
        self.base_folder_name = base_folder_name
        
        return destination_folder

    def _get_unique_folder_name(self, folder_path):
        """Append a unique (i) to folder name if it already exists."""
        base_folder_path = folder_path
        i = 1
        while os.path.exists(folder_path):
            folder_path = f"{base_folder_path} ({i})"
            i += 1
        return folder_path

    def _get_unique_file_name(self, file_path):
        """Append a unique (i) to file name if it already exists."""
        base, extension = os.path.splitext(file_path)
        i = 1
        new_file_path = file_path
        while os.path.exists(new_file_path):
            new_file_path = f"{base} ({i}){extension}"
            i += 1
        return new_file_path
    #com.an.Datadash


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

class ReceiveAppPJava(QWidget):
    progress_update = pyqtSignal(int)

    def __init__(self, client_ip):
        super().__init__()
        self.client_ip = client_ip
        self.initUI()
        self.setFixedSize(853, 480)
        
        self.current_text = "Waiting to Receive files from Android"  # The full text for the label
        self.displayed_text = ""  # Text that will appear with typewriter effect
        self.char_index = 0  # Keeps track of the character index for typewriter effect
        self.progress_bar.setVisible(False)  # Initially hidden
        
        self.file_receiver = ReceiveWorkerJava(client_ip)
        self.file_receiver.progress_update.connect(self.updateProgressBar)
        self.file_receiver.decrypt_signal.connect(self.decryptor_init)
        self.file_receiver.receiving_started.connect(self.show_progress_bar)  # Connect new signal
        #com.an.Datadash
       
        
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
        #com.an.Datadash
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

        self.mainmenu_button = self.create_styled_button('Main Menu')
        self.mainmenu_button.setVisible(False)
        self.mainmenu_button.clicked.connect(self.openMainWindow)
        layout.addWidget(self.mainmenu_button)

        self.setLayout(layout)

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
        #com.an.Datadash
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
            # self.mainmenu_button.setVisible(True)

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
        receiving_dir = get_config().get("save_to_directory", "")
        
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
            
            except FileNotFoundError as fnfe:
                logger.error("No file manager or terminal emulator found on Linux: %s", fnfe)
            except Exception as e:
                logger.error("Failed to open directory: %s", str(e))
        else:
            logger.error("No receiving directory configured.")

    def show_error_message(self, title, message, detailed_text):
        QMessageBox.critical(self, title, message)

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
        except:
            pass

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    receive_app = ReceiveAppPJava()
    receive_app.show()
    app.exec()