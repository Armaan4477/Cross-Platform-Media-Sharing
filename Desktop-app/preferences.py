from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QCheckBox, QHBoxLayout, QMessageBox, QApplication
)
from PyQt6.QtGui import QScreen, QFont, QColor
from PyQt6.QtCore import Qt
import sys
import platform
from constant import get_config, write_config, get_default_path
from PyQt6.QtWidgets import QGraphicsDropShadowEffect

class PreferencesApp(QWidget):
    def __init__(self):
        super().__init__()
        self.original_preferences = {}
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Preferences')
        self.setGeometry(100, 100, 500, 400)  # Adjusted window size for larger elements
        self.center_window()
        self.set_background()

        layout = QVBoxLayout()
        #layout.setSpacing(0)  # Set the spacing between widgets to 0
        #layout.setContentsMargins(0, 0, 0, 0)  # Set the margins to 0


        # Device Name
        self.device_name_label = QLabel('Device Name:', self)
        self.device_name_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        self.style_label(self.device_name_label)
        layout.addWidget(self.device_name_label)

        self.device_name_input = QLineEdit(self)
        self.device_name_input.setFont(QFont("Arial", 16))
        self.device_name_input.setFixedHeight(30)
        self.style_input(self.device_name_input)
        layout.addWidget(self.device_name_input)

        self.device_name_reset_button = QPushButton('Reset', self)
        self.device_name_reset_button.setFont(QFont("Arial", 12))
        self.device_name_reset_button.setFixedSize(120, 40)
        self.device_name_reset_button.clicked.connect(self.resetDeviceName)
        self.style_button(self.device_name_reset_button)
        layout.addWidget(self.device_name_reset_button)

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

        # Submit and Main Menu buttons
        buttons_layout = QHBoxLayout()

        self.main_menu_button = QPushButton('Main Menu', self)
        self.main_menu_button.setFont(QFont("Arial", 12))
        self.main_menu_button.setFixedSize(150, 50)
        self.main_menu_button.clicked.connect(self.goToMainMenu)
        self.style_button(self.main_menu_button)
        buttons_layout.addWidget(self.main_menu_button)

        self.submit_button = QPushButton('Submit', self)
        self.submit_button.setFont(QFont("Arial", 12))
        self.submit_button.setFixedSize(150, 50)
        self.submit_button.clicked.connect(self.submitPreferences)
        self.style_button(self.submit_button)
        buttons_layout.addWidget(self.submit_button)

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
            color: #FFFFFF;
            background-color: transparent;  /* Set the background to transparent */
            border: 1px solid #444;  /* Retain the border for input fields */
            border-radius: 8px;
            padding: 5px;
        """)




    def style_checkbox(self, checkbox):
        checkbox.setGraphicsEffect(self.create_glow_effect())
        checkbox.setStyleSheet("""
        color: #FFFFFF;
        background-color: transparent;  /* Set the background to transparent */
        """)


    def style_button(self, button):
        button.setFixedSize(150, 50)
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
                border: 2px solid rgba(0, 0, 0, 0.5);
                padding: 10px;
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

    def goToMainMenu(self):
        if self.changes_made():
            reply = QMessageBox.question(
                self,
                "Save Changes",
                "Do you want to save changes before returning to the main menu?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel
            )
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

    def submitPreferences(self):
        device_name = self.device_name_input.text()
        save_to_path = self.save_to_path_input.text()
        encryption = self.encryption_toggle.isChecked()

        if not device_name:
            QMessageBox.critical(self, "Input Error", "Device Name cannot be empty.")
            return

        preferences = {
            "device_name": device_name,
            "save_to_directory": save_to_path,
            "encryption": encryption
        }

        write_config(preferences)
        QMessageBox.information(self, "Success", "Preferences saved successfully!")
        self.go_to_main_menu()

    def center_window(self):
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        window_width, window_height = 500, 400
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2
        self.setGeometry(x, y, window_width, window_height)

    def loadPreferences(self):
        config = get_config()
        self.device_name_input.setText(config["device_name"])
        self.save_to_path_input.setText(config["save_to_directory"])
        self.encryption_toggle.setChecked(config["encryption"])
        self.original_preferences = config.copy()

    def changes_made(self):
        current_preferences = {
            "device_name": self.device_name_input.text(),
            "save_to_directory": self.save_to_path_input.text(),
            "encryption": self.encryption_toggle.isChecked(),
        }
        return current_preferences != self.original_preferences

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PreferencesApp()
    window.show()
    sys.exit(app.exec())
