from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QApplication,
                             QLabel, QFrame, QGraphicsDropShadowEffect, QMessageBox)
from PyQt6.QtGui import QScreen, QFont, QPalette, QPainter, QColor, QPen, QIcon, QLinearGradient, QPainterPath
from PyQt6.QtCore import Qt, QTimer, QSize
import sys
import os
from file_receiver import ReceiveApp
from file_sender import SendApp
from broadcast import Broadcast
from preferences import PreferencesApp
from credits_dialog import CreditsDialog
from constant import logger, get_config
from PyQt6.QtSvg import QSvgRenderer
import math

class WifiAnimationWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(550, 500)
        self.signal_strength = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_signal)
        self.timer.start(35)

    def update_signal(self):
        self.signal_strength = (self.signal_strength + 1.5) % 145
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center = self.rect().center()
        max_radius = min(self.width(), self.height()) // 2

        for i in range(3):
            radius = max_radius * (i + 1) // 3
            opacity = min(1, self.signal_strength / 100 * 3 - i)
            painter.setPen(QPen(QColor(255, 255, 255, int(opacity * 255)), 2))
            painter.drawArc(center.x() - radius, center.y() - max_radius // 2 - radius,
                            radius * 2, radius * 2, 0, 180 * 16)
            
class IconButton(QPushButton):
    def __init__(self, color_start=(77, 84, 96), color_end=(105, 115, 128), parent=None):
        super().__init__(parent)
        self.setFixedSize(42, 42)
        self.color_start = color_start
        self.color_end = color_end
        #self.glow()
        self.setToolTip("<b style='color: #FFA500; font-size: 14px;'>Settings</b><br><i style='font-size: 12px;'>Click to configure</i>")

    def glow(self):
        glow_effect = QGraphicsDropShadowEffect()
        glow_effect.setBlurRadius(15)
        glow_effect.setXOffset(0)
        glow_effect.setYOffset(0)
        glow_effect.setColor(QColor(255, 255, 255, 100))
        self.setGraphicsEffect(glow_effect)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Set the gradient brush for the circles
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(*self.color_start))
        gradient.setColorAt(1, QColor(*self.color_end))

        # Draw the circles first
        painter.setBrush(gradient)
        painter.setPen(QPen(QColor(0, 0, 0, 0)))  # Set pen to transparent

        # Draw a settings (gear) icon
        path = QPainterPath()

        # Create a gear shape
        center_x, center_y = 19, 19  # Center coordinates
        inner_radius = 7               # Inner radius
        outer_radius = 12              # Outer radius
        tooth_length = 5               # Length of the teeth
        tooth_width = 17               # Width of the teeth

        # Draw outer circle
        path.addEllipse(center_x - outer_radius, center_y - outer_radius, outer_radius * 2, outer_radius * 2)

        # Draw inner circle
        path.addEllipse(center_x - inner_radius, center_y - inner_radius, inner_radius * 2, inner_radius * 2)

        # Draw gear teeth square shape (rectangle), 6 teeth in total, 1 tooth = 60 degrees, 30 degrees for each side,first tooth at 90 degrees
        for i in range(6):
            angle = 81 + i * 60
            x1 = center_x + inner_radius * math.cos(math.radians(angle))
            y1 = center_y + inner_radius * math.sin(math.radians(angle))
            x2 = center_x + outer_radius * math.cos(math.radians(angle))
            y2 = center_y + outer_radius * math.sin(math.radians(angle))
            x3 = center_x + (outer_radius + tooth_length) * math.cos(math.radians(angle))
            y3 = center_y + (outer_radius + tooth_length) * math.sin(math.radians(angle))
            x4 = center_x + (outer_radius + tooth_length) * math.cos(math.radians(angle + tooth_width))
            y4 = center_y + (outer_radius + tooth_length) * math.sin(math.radians(angle + tooth_width))
            x5 = center_x + outer_radius * math.cos(math.radians(angle + tooth_width))
            y5 = center_y + outer_radius * math.sin(math.radians(angle + tooth_width))
            x6 = center_x + inner_radius * math.cos(math.radians(angle + tooth_width))
            y6 = center_y + inner_radius * math.sin(math.radians(angle + tooth_width))

            path.moveTo(x1, y1)
            path.lineTo(x2, y2)
            path.lineTo(x3, y3)
            path.lineTo(x4, y4)
            path.lineTo(x5, y5)
            path.lineTo(x6, y6)
            path.lineTo(x1, y1)

        painter.drawPath(path)

class MainApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.setFixedSize(853, 480) 

    def initUI(self):
        self.setWindowTitle('DataDash')
        self.setGeometry(100, 100, 853, 480)
        self.center_window()
        self.set_background()

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QFrame()
        header.setFixedHeight(70)
        header.setStyleSheet("background-color: #333; padding: 0px;")
        header_layout = QHBoxLayout(header)

        # Create and add the IconButton instead of using SvgButton
        icon_button = IconButton()  # Example colors
        icon_button.clicked.connect(self.openSettings)  # Connect the clicked signal to the handler
        header_layout.addWidget(icon_button, alignment=Qt.AlignmentFlag.AlignLeft)

        # Add a stretch after the settings button
        header_layout.addStretch()

        # Title label
        title_label = QLabel("DataDash: CrossPlatform Data Sharing")
        title_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        title_label.setStyleSheet("color: white;")
        header_layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Add another stretch after the title to balance the layout
        header_layout.addStretch()

        main_layout.addWidget(header)

        # Add some vertical space before the WiFi Animation Widget
        main_layout.addSpacing(105)

        # Wifi Animation Widget
        wifi_widget = WifiAnimationWidget()
        main_layout.addWidget(wifi_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        icon_path_send = os.path.join(os.path.dirname(__file__), "assets", "send.svg")
        icon_path_receive = os.path.join(os.path.dirname(__file__), "assets", "receive.svg")


        # Buttons Layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)  # Reduced spacing between Send and Receive buttons
        button_layout.setContentsMargins(30, 0, 30, 0)

        # Send File Button
        self.send_button = QPushButton('Send File')
        self.send_button.setIcon(QIcon(icon_path_send))
        self.send_button.setIconSize(QSize(24, 24))  # Adjust icon size as needed
        self.style_button(self.send_button)
        self.send_button.clicked.connect(self.sendFile)
        self.send_button.setToolTip("<b style='color: #FFA500; font-size: 14px;'>Send File</b><br><i style='font-size: 12px;'>Send a folder or multiple files to another device</i>")
        button_layout.addWidget(self.send_button)

        # Receive File Button
        self.receive_button = QPushButton('Receive File')
        self.receive_button.setIcon(QIcon(icon_path_receive))
        self.receive_button.setIconSize(QSize(24, 24))  # Adjust icon size as needed
        self.style_button(self.receive_button)
        self.receive_button.clicked.connect(self.receiveFile)
        self.receive_button.setToolTip("<b style='color: #FFA500; font-size: 14px;'>Receive File</b><br><i style='font-size: 12px;'>Receive a folder or multiple files from another device</i>")
        button_layout.addWidget(self.receive_button)

        # Add the first button layout to the main layout
        main_layout.addLayout(button_layout)

        # Add some vertical space above the Credits button layout
        main_layout.addSpacing(20)  # Moves buttons up and adds spacing between buttons and Credits

        self.setLayout(main_layout)
        logger.info("Started Main App")

    def style_button(self, button):
        button.setFixedSize(150, 50)
        button.setFont(QFont("Arial", 15))
        button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(47, 54, 66, 255),
                    stop: 1 rgba(75, 85, 98, 255)
                );
                color: white;
                border-radius: 25px;
                border: 1px solid rgba(0, 0, 0, 0.5);
                padding: 6px;
                font-weight: bold;
                font-size: 14px;
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

        glow_effect = QGraphicsDropShadowEffect()
        glow_effect.setBlurRadius(15)
        glow_effect.setXOffset(0)
        glow_effect.setYOffset(0)
        glow_effect.setColor(QColor(255, 255, 255, 100))
        button.setGraphicsEffect(glow_effect)

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

    def center_window(self):
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        window_width, window_height = 853, 480  # Changed from 700 to 853 for 16:9 ratio
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2
        self.setGeometry(x, y, window_width, window_height)

        dest = get_config()["save_to_directory"]
        if not os.path.exists(dest):
            os.makedirs(dest)
            logger.info("Created folder to receive files")

    def sendFile(self):
        # Check if warnings should be shown
        if get_config()["show_warning"]:
            send_dialog = QMessageBox(self)
            send_dialog.setWindowTitle("Note")
            send_dialog.setText("""Before starting the transfer, please ensure both the sender and receiver devices are connected to the same network.
            """)
            send_dialog.setIcon(QMessageBox.Icon.Warning)

            # Add buttons
            proceed_button = send_dialog.addButton("Proceed", QMessageBox.ButtonRole.AcceptRole)
            cancel_button = send_dialog.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)

            # Apply consistent styling with a gradient background and transparent text area
            send_dialog.setStyleSheet("""
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
                    background-color: transparent;  /* Transparent text background */
                    font-size: 16px;
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

            # Execute dialog and handle response
            send_dialog.exec()
            if send_dialog.clickedButton() == proceed_button:
                logger.info("Started Send File App")
                self.hide()
                self.broadcast_app = Broadcast()
                self.broadcast_app.show()
        else:
            logger.info("Started Send File App without warning")
            self.hide()
            self.broadcast_app = Broadcast()
            self.broadcast_app.show()

    def receiveFile(self):
        # Check if warnings should be shown
        if get_config()["show_warning"]:
            receive_dialog = QMessageBox(self)
            receive_dialog.setWindowTitle("Note")
            receive_dialog.setText("""Before starting the transfer, please ensure both the sender and receiver devices are connected to the same network.
            """)
            receive_dialog.setIcon(QMessageBox.Icon.Warning)

            # Add buttons
            proceed_button = receive_dialog.addButton("Proceed", QMessageBox.ButtonRole.AcceptRole)
            cancel_button = receive_dialog.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)

            # Apply consistent styling with a gradient background and transparent text area
            receive_dialog.setStyleSheet("""
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
                    background-color: transparent;  /* Transparent text background */
                    font-size: 16px;
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

            # Execute dialog and handle response
            receive_dialog.exec()
            if receive_dialog.clickedButton() == proceed_button:
                logger.info("Started Receive File App")
                self.hide()
                self.receive_app = ReceiveApp()
                self.receive_app.show()
        else:
            logger.info("Started Receive File App without warning")
            self.hide()
            self.receive_app = ReceiveApp()
            self.receive_app.show()




    def preferences_handler(self):
        logger.info("Started Preferences handler menu")
        self.hide()
        self.preferences_app = PreferencesApp()
        self.preferences_app.show()

    def show_credits(self):
        logger.info("Opened Credits Dialog")
        credits_dialog = CreditsDialog()
        credits_dialog.exec()

    def openSettings(self):
        logger.info("Settings button clicked")
        self.preferences_handler()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main = MainApp()
    main.show()
    sys.exit(app.exec()) 