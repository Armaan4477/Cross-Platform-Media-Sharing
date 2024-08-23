from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QApplication
from PyQt6.QtGui import QScreen
from file_receiver import ReceiveApp
from file_sender import SendApp
from broadcast import Broadcast
from preferences import PreferencesApp
import sys
import os
import platform
from constant import logger,get_config

class MainApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Media Sharing App')
        self.setGeometry(100, 100, 300, 200)
        self.center_window()

        layout = QVBoxLayout()

        self.send_button = QPushButton('Send File', self)
        self.send_button.clicked.connect(self.sendFile)
        layout.addWidget(self.send_button)

        self.receive_button = QPushButton('Receive File', self)
        self.receive_button.clicked.connect(self.receiveFile)
        layout.addWidget(self.receive_button)

        self.preferences_button = QPushButton('Preferences', self)
        self.preferences_button.clicked.connect(self.preferences_handler)
        layout.addWidget(self.preferences_button)

        self.setLayout(layout)
        logger.info("Started Main App")

    def center_window(self):

    #    if platform.system() == 'Windows':
               
    #    elif platform.system() == 'Linux':
                
    #    elif platform.system() == 'Darwin':
                

        # screen = QApplication.primaryScreen()
        # screen_geometry = screen.availableGeometry()
        # screen_width = screen_geometry.width()
        # screen_height = screen_geometry.height()

        # window_width = 800
        # window_height = 600

        # x = (screen_width - window_width) / 2
        # y = (screen_height - window_height) / 2

        # self.setGeometry(int(x), int(y), window_width, window_height)

        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        window_width, window_height = 800, 600
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2
        self.setGeometry(x, y, window_width, window_height)

        #Check if the folder to receive files exists
        dest = get_config()["save_to_directory"]
        if not os.path.exists(dest):
            os.makedirs(dest)
            logger.info("Created folder to receive files")

    def sendFile(self):
        logger.info("Started Send File App")
        self.hide()
        # Call the broadcast screen
        self.broadcast_app = Broadcast()
        self.broadcast_app.show()
        # Call broadcast receiver 
        # self.send_app = SendApp()
        # self.send_app.show()

    def receiveFile(self):
        logger.info("Started Receive File App")
        self.hide()
        self.receive_app = ReceiveApp()
        self.receive_app.show()

    def preferences_handler(self):
        logger.info("Started Preferences handler menu")
        self.hide()
        self.preferences_app = PreferencesApp()
        self.preferences_app.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main = MainApp()
    main.show()
    sys.exit(app.exec())