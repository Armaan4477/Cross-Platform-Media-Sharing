from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QCheckBox, QHBoxLayout, QMessageBox, QApplication
)
from PyQt6.QtGui import QScreen, QFont, QColor
from PyQt6.QtCore import Qt
import sys
import platform
from constant import get_config, write_config, get_default_path
from PyQt6.QtWidgets import QGraphicsDropShadowEffect
from credits_dialog import CreditsDialog
from constant import logger

class PreferencesApp(QWidget):
    def __init__(self):
        super().__init__()
        self.original_preferences = {}
        self.initUI()
        self.setFixedSize(500, 450)  # Adjusted height to accommodate new toggle

    def initUI(self):
        self.setWindowTitle('Settings')
        self.setGeometry(100, 100, 500, 450)  # Adjusted height to accommodate new toggle
        self.center_window()
        self.set_background()

        layout = QVBoxLayout()

        # Help button layout at the top right
        help_button_layout = QHBoxLayout()
        help_button_layout.addStretch()  # Adds a spacer that pushes the button to the right
        
        # Create the Help button
        self.help_button = QPushButton('Help', self)
        self.help_button.setFont(QFont("Arial", 10))
        self.help_button.setFixedSize(80, 30)
        self.style_help_button(self.help_button)
        self.help_button.clicked.connect(self.show_help_dialog)

        help_button_layout.addWidget(self.help_button)
        layout.addLayout(help_button_layout)

        # Device Name
        self.device_name_label = QLabel('Device Name:', self)
        self.device_name_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        self.style_label(self.device_name_label)
        layout.addWidget(self.device_name_label)

        # Horizontal layout for device name input and reset button
        device_name_layout = QHBoxLayout()

        self.device_name_input = QLineEdit(self)
        self.device_name_input.setFont(QFont("Arial", 16))
        self.device_name_input.setFixedHeight(30)
        self.style_input(self.device_name_input)
        device_name_layout.addWidget(self.device_name_input)

        self.device_name_reset_button = QPushButton('Reset', self)
        self.device_name_reset_button.setFont(QFont("Arial", 12))
        self.device_name_reset_button.setFixedSize(120, 40)
        self.device_name_reset_button.clicked.connect(self.resetDeviceName)
        self.style_button(self.device_name_reset_button)
        device_name_layout.addWidget(self.device_name_reset_button)

        layout.addLayout(device_name_layout)

        # Save to Path
        self.save_to_path_label = QLabel('Save to Path:', self)
        self.save_to_path_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        self.style_label(self.save_to_path_label)
        layout.addWidget(self.save_to_path_label)

        self.save_to_path_input = QLineEdit(self)
        self.save_to_path_input.setFont(QFont("Arial", 16))
        self.save_to_path_input.setFixedHeight(30)
        self.style_input(self.save_to_path_input)
        layout.addWidget(self.save_to_path_input)

        path_layout = QHBoxLayout()
        self.save_to_path_picker_button = QPushButton('Pick Directory', self)
        self.save_to_path_picker_button.setFont(QFont("Arial", 12))
        self.save_to_path_picker_button.setFixedSize(150, 40)
        self.save_to_path_picker_button.clicked.connect(self.pickDirectory)
        self.style_button(self.save_to_path_picker_button)
        path_layout.addWidget(self.save_to_path_picker_button)

        self.save_to_path_reset_button = QPushButton('Reset', self)
        self.save_to_path_reset_button.setFont(QFont("Arial", 12))
        self.save_to_path_reset_button.setFixedSize(120, 40)
        self.save_to_path_reset_button.clicked.connect(self.resetSavePath)
        self.style_button(self.save_to_path_reset_button)
        path_layout.addWidget(self.save_to_path_reset_button)

        layout.addLayout(path_layout)

        # Encryption Toggle
        self.encryption_toggle = QCheckBox('Encryption', self)
        self.encryption_toggle.setFont(QFont("Arial", 18))
        self.style_checkbox(self.encryption_toggle)
        layout.addWidget(self.encryption_toggle)

        # Show Warning Toggle
        self.show_warning_toggle = QCheckBox('Show Warnings', self)
        self.show_warning_toggle.setFont(QFont("Arial", 18))
        self.style_checkbox(self.show_warning_toggle)
        layout.addWidget(self.show_warning_toggle)

        # Submit and Main Menu buttons
        buttons_layout = QHBoxLayout()

        self.main_menu_button = QPushButton('Main Menu', self)
        self.main_menu_button.setFont(QFont("Arial", 12))
        self.main_menu_button.setFixedSize(150, 50)
        self.main_menu_button.clicked.connect(self.goToMainMenu)
        self.style_button(self.main_menu_button)
        buttons_layout.addWidget(self.main_menu_button)

        # Credits Button
        self.credits_button = QPushButton('Credits')
        self.credits_button.setFont(QFont("Arial", 12))
        self.style_button(self.credits_button)
        self.credits_button.clicked.connect(self.show_credits)
        buttons_layout.addWidget(self.credits_button)

        layout.addLayout(buttons_layout)

        self.setLayout(layout)
        self.loadPreferences()

    def style_label(self, label):
        label.setStyleSheet("""
            color: #FFFFFF;
            background-color: transparent;  /* Set the background to transparent */
        """)

    def style_input(self, input_field):
        input_field.setStyleSheet("""
            QLineEdit {
                color: #FFFFFF;
                background-color: transparent;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 5px;
                caret-color: #00FF00;  /* Green cursor color */
            }
            QLineEdit:focus {
                border: 2px solid #333333;  /* Dark grey border on focus */
                caret-color: #00FF00;  /* Green cursor color on focus */
                background-color: rgba(255, 255, 255, 0.1); /* Slightly opaque background on focus */
            }
        """)

    def style_checkbox(self, checkbox):
        checkbox.setGraphicsEffect(self.create_glow_effect())
        checkbox.setStyleSheet("""
        color: #FFFFFF;
        background-color: transparent;  /* Set the background to transparent */
        """)

    def style_button(self, button):
        button.setFixedSize(150, 50)
        button.setFont(QFont("Arial", 15))
        button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(47, 54, 66, 255),   /* Dark Color */
                    stop: 1 rgba(75, 85, 98, 255)    /* Light Color */
                );
                color: white;
                border-radius: 25px;
                border: 1px solid rgba(0, 0, 0, 0.5);
                padding: 6px;
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
        button.setGraphicsEffect(self.create_glow_effect())

    def style_help_button(self, button):
        button.setFixedSize(60, 30)
        button.setFont(QFont("Arial", 12))
        button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(47, 54, 66, 255),   /* Dark Color */
                    stop: 1 rgba(75, 85, 98, 255)    /* Light Color */
                );
                color: white;
                border-radius: 12px;
                border: 1px solid rgba(0, 0, 0, 0.5);
                padding: 6px;
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
        button.setGraphicsEffect(self.create_glow_effect())

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

    def create_glow_effect(self):
        glow_effect = QGraphicsDropShadowEffect()
        glow_effect.setBlurRadius(15)
        glow_effect.setXOffset(0)
        glow_effect.setYOffset(0)
        glow_effect.setColor(QColor(255, 255, 255, 100))
        return glow_effect

    def resetDeviceName(self):
        self.device_name_input.setText(platform.node())

    def pickDirectory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            self.save_to_path_input.setText(directory)

    def resetSavePath(self):
        self.save_to_path_input.setText(get_default_path())

    def loadPreferences(self):
        config = get_config()
        self.version = config["version"]
        self.device_name_input.setText(config["device_name"])
        self.save_to_path_input.setText(config["save_to_directory"])
        self.encryption_toggle.setChecked(config["encryption"])
        self.android_encryption=(config["android_encryption"])
        self.show_warning_toggle.setChecked(config["show_warning"])  # Load show_warning value
        self.original_preferences = config.copy()
        logger.info("Loaded preferences: %s", self.version)
        logger.info("Loaded preferences: %s", self.android_encryption)

    def submitPreferences(self):
        device_name = self.device_name_input.text()
        save_to_path = self.save_to_path_input.text()
        encryption = self.encryption_toggle.isChecked()
        show_warning = self.show_warning_toggle.isChecked()  # Get show_warning toggle state

        if not device_name:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Input Error")
            msg_box.setText("Device Name cannot be empty.")
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

        preferences = {
            "version": self.version,
            "device_name": device_name,
            "save_to_directory": save_to_path,
            "encryption": encryption,
            "android_encryption": self.android_encryption,
            "show_warning": show_warning  # Save show_warning state
        }

        write_config(preferences)
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Success")
        msg_box.setText("Preferences saved successfully!")
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)

        # Apply custom style with gradient background and transparent text area
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
        self.go_to_main_menu()


    def goToMainMenu(self):
        if self.changes_made():
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Save Changes")
            msg_box.setText("Do you want to save changes before returning to the main menu?")
            msg_box.setIcon(QMessageBox.Icon.Question)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)

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

            reply = msg_box.exec()
            if reply == QMessageBox.StandardButton.Yes:
                self.submitPreferences()
                self.go_to_main_menu()
            elif reply == QMessageBox.StandardButton.No:
                self.go_to_main_menu()
        else:
            self.go_to_main_menu()



    def go_to_main_menu(self):
        self.hide()
        from main import MainApp
        self.main_app = MainApp()
        self.main_app.show()

    
    def center_window(self):
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        window_width, window_height = 500, 400
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2
        self.setGeometry(x, y, window_width, window_height)


    def changes_made(self):
        current_preferences = {
            "version": self.version,
            "device_name": self.device_name_input.text(),
            "save_to_directory": self.save_to_path_input.text(),
            "encryption": self.encryption_toggle.isChecked(),
            "android_encryption": self.android_encryption,
            "show_warning": self.show_warning_toggle.isChecked()  # Get show_warning toggle state
        }
        return current_preferences != self.original_preferences
    
    def show_credits(self):
        logger.info("Opened Credits Dialog")
        credits_dialog = CreditsDialog()
        credits_dialog.exec()

    def show_help_dialog(self):
        help_dialog = QMessageBox(self)
        help_dialog.setWindowTitle("Help")
        help_dialog.setText("""
        <b>Device Name:</b> The name assigned to this device. You can reset it to the system's default.
        <br><br>
        <b>Save to Path:</b> Choose a directory to save your files. You can also reset it to the default path.
        <br><br>
        <b>Encryption:</b> Enable or disable AES256 encryption for files being sent.
        <br><br>
        <b>Show Warnings:</b> Enable or disable warning messages before sending or receiving files.
        <br><br>
        <b>Main Menu:</b> Go back to the main application window. You will be prompted to save changes if any.
        <br><br>
        <b>Credits:</b> View credits for the application.
        """)
        help_dialog.setIcon(QMessageBox.Icon.Information)

        # Apply consistent styling with a gradient background and transparent text area
        help_dialog.setStyleSheet("""
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
        help_dialog.exec()



if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PreferencesApp()
    window.show()
    sys.exit(app.exec())
