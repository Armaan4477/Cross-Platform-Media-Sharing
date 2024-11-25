import os
import platform
import socket
import struct
import threading
from PyQt6.QtCore import QThread, pyqtSignal,QTimer,Qt
from PyQt6 import QtCore
from PyQt6.QtWidgets import (
    QMessageBox, QWidget, QVBoxLayout, QLabel, QProgressBar, QApplication,QHBoxLayout
)
from PyQt6.QtGui import QScreen, QMovie, QKeySequence, QKeyEvent
from constant import get_config, logger
from crypt_handler import decrypt_file, Decryptor
from time import sleep
import json
from file_receiver_python import ReceiveAppP
from file_receiver_android import ReceiveAppPJava

SENDER_JSON = 53000
RECEIVER_JSON = 54000
LISTEN_PORT = 12346

class FileReceiver(QThread):
    show_receive_app_p_signal = pyqtSignal()  # Signal to show the ReceiveAppP window
    show_receive_app_p_signal_java = pyqtSignal()  # Signal to show the ReceiveAppP window for Java devices

    def __init__(self):
        super().__init__()
        self.encrypted_files = []
        self.broadcasting = True
        self.metadata = None
        self.destination_folder = None
        self.client_ip = None
        self.server_socket = None
        self.client_socket = None
        self.receiver_worker = None

    def run(self):
        # Clear all connections on the about to be used ports 
        try:
            if self.server_socket:
                self.server_socket.close()
                sleep(0.5)
            if self.client_socket:
                self.client_socket.close()
                sleep(0.5)
            if self.receiver_worker:
                self.receiver_worker.terminate()
        except Exception as e:
            pass

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allow immediate reuse of the address
        self.server_socket.bind(('0.0.0.0', RECEIVER_JSON))
        self.server_socket.listen(5)  # Listen for multiple connections

        while True:
            self.client_socket, addr = self.server_socket.accept()
            self.store_client_ip()
            self.handle_device_type()
            self.client_socket.close()  # Close the connection after receiving files

    def store_client_ip(self):
        """Extract and store the IP address of the connected client."""
        self.client_ip = self.client_socket.getpeername()[0]
        logger.debug(f"Client IP address stored: {self.client_ip}")
        return self.client_ip

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
        # print logger info of client_socket ip address
        logger.debug(f"Connected to {self.client_socket.getpeername()}")

        # Receive and process the device information from the sender
        device_json_size = struct.unpack('<Q', self.client_socket.recv(8))[0]
        device_json = self.client_socket.recv(device_json_size).decode()
        self.device_info = json.loads(device_json)
        sender_device_type = self.device_info.get("device_type", "unknown")
        if sender_device_type == "python":
            logger.debug("Connected to a Python device.")
            self.show_receive_app_p_signal.emit()
            sleep(1)  # Wait for the signal to be processed
            self.cleanup_sockets() # Clean up before proceeding
        elif sender_device_type == "java":
            logger.debug("Connected to a Java device, but this feature is not implemented yet.")
            self.show_receive_app_p_signal_java.emit()
            sleep(1)
            self.cleanup_sockets()
        else:
            logger.debug("Unknown device type received.")
    
    def cleanup_sockets(self):
        if self.client_socket:
            self.client_socket.close()



class ReceiveApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.setFixedSize(853, 480)
        self.config = get_config()  # Load config once
        #com.an.Datadash

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

        gif_path = os.path.join(os.path.dirname(__file__), "assets", "loading.gif")
       
        layout = QVBoxLayout()

        hbox = QHBoxLayout()
        
        self.loading_label = QLabel(self)
        self.loading_label.setStyleSheet("QLabel { background-color: transparent; border: none; }")
        self.movie = QMovie(gif_path)  # Use the relative path to load the GIF
        self.movie.setScaledSize(QtCore.QSize(40, 40)) 
        self.loading_label.setMovie(self.movie)
        self.movie.start()
        hbox.addWidget(self.loading_label)

        # Label with typewriter effect
        self.label = QLabel("", self)  # Empty string initially
        self.label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 28px;
                background: transparent;
                border: none;
                font-weight: bold;
            }
        """)
        hbox.addWidget(self.label)
        hbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addLayout(hbox)
        self.setLayout(layout)


        #layout = QVBoxLayout()

        # self.label = QLabel("Waiting for Connection...", self)
        # layout.addWidget(self.label)

        self.setLayout(layout)

        self.file_receiver = FileReceiver()
        self.file_receiver.show_receive_app_p_signal.connect(self.show_receive_app_p)  # Connect the signal to the slot
        self.file_receiver.show_receive_app_p_signal_java.connect(self.show_receive_app_p_java)
        self.file_receiver.start()
        #com.an.Datadash

        self.broadcast_thread = threading.Thread(target=self.listenForBroadcast, daemon=True)
        self.broadcast_thread.start()
# Call the method to start typewriter effect
        self.start_typewriter_effect("Waiting for Connection...")

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.openMainWindow()

    def openMainWindow(self):
        from main import MainApp
        self.main_app = MainApp()
        self.main_app.show()
        self.close()

    def start_typewriter_effect(self, full_text, interval=100):
        """Starts the typewriter effect to show text character by character."""
        self.full_text = full_text
        self.text_index = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_text)
        self.timer.start(interval)

    def update_text(self):
        """Updates the label with one more character."""
        self.text_index += 1
        self.label.setText(self.full_text[:self.text_index])
        if self.text_index >= len(self.full_text):
            self.timer.stop()
            #com.an.Datadash

    def listenForBroadcast(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('', LISTEN_PORT))

            while True:
                if self.file_receiver.broadcasting:
                    message, address = s.recvfrom(1024)
                    message = message.decode()
                    if message == 'DISCOVER':
                        response = f'RECEIVER:{self.config["device_name"]}'
                        # Use the same socket and port to send response
                        s.sendto(response.encode(), (address[0], LISTEN_PORT))
                sleep(1)  # Avoid busy-waiting

    def connection_successful(self):
        self.movie.stop()
        self.loading_label.hide()
        self.label.setText("Connected successfully!")
        self.label.setStyleSheet("color: #00FF00;")  # Green color for success
        #com.an.Datadash


    def show_receive_app_p(self):
        client_ip = self.file_receiver.client_ip
        """Slot to show the ReceiveAppP window on the main thread."""
        self.hide()
        self.receive_app_p = ReceiveAppP(client_ip)
        self.receive_app_p.show()

    def show_receive_app_p_java(self):
        client_ip = self.file_receiver.client_ip
        """Slot to show the ReceiveAppP window on the main thread."""
        self.hide()
        self.receive_app_p_java = ReceiveAppPJava(client_ip)
        self.receive_app_p_java.show()

    def center_window(self):
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        window_width, window_height = 853, 480
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2
        self.setGeometry(x, y, window_width, window_height)

    def closeEvent(self, event):
        try:
            """Override the close event to ensure everything is stopped properly."""
            if self.file_receiver:
                self.file_receiver.terminate()
                self.stop()
        except AttributeError:
            pass
        # Stop the broadcasting thread
        self.file_receiver.broadcasting = False
        event.accept()

    def stop(self):
        self.file_receiver.broadcasting = False
        self.file_receiver.server_socket.close()
        self.file_receiver.client_socket.close()
        self.file_receiver.receiver_worker.terminate()

if __name__ == '__main__':
    import sys
    app = QApplication([])
    receive_app = ReceiveApp()
    receive_app.show()
    app.exec()
    #com.an.Datadash