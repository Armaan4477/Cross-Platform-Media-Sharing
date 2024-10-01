from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QSpinBox, QCheckBox, QHBoxLayout, QMessageBox, QApplication
)
from PyQt6.QtGui import QScreen
from PyQt6.QtCore import Qt
import sys
import json
import os
import platform
from constant import get_config, write_config, get_default_path

class PreferencesApp(QWidget):
    def __init__(self):
        super().__init__()
        self.original_preferences = {}
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Preferences')
        self.setGeometry(100, 100, 400, 300)
        self.center_window()

        layout = QVBoxLayout()

        # Device Name
        self.device_name_label = QLabel('Device Name:', self)
        layout.addWidget(self.device_name_label)

        self.device_name_input = QLineEdit(self)
        layout.addWidget(self.device_name_input)

        self.device_name_reset_button = QPushButton('Reset', self)
        self.device_name_reset_button.clicked.connect(self.resetDeviceName)
        layout.addWidget(self.device_name_reset_button)

        # Save to Path
        self.save_to_path_label = QLabel('Save to Path:', self)
        layout.addWidget(self.save_to_path_label)

        self.save_to_path_input = QLineEdit(self)
        layout.addWidget(self.save_to_path_input)

        path_layout = QHBoxLayout()
        self.save_to_path_picker_button = QPushButton('Pick Directory', self)
        self.save_to_path_picker_button.clicked.connect(self.pickDirectory)
        path_layout.addWidget(self.save_to_path_picker_button)

        self.save_to_path_reset_button = QPushButton('Reset', self)
        self.save_to_path_reset_button.clicked.connect(self.resetSavePath)
        path_layout.addWidget(self.save_to_path_reset_button)
        layout.addLayout(path_layout)

        # Encryption Toggle
        self.encryption_toggle = QCheckBox('Encryption', self)
        layout.addWidget(self.encryption_toggle)

        # submit and main menu button
        buttons_layout = QHBoxLayout()

        self.main_menu_button = QPushButton('Main Menu', self)
        self.main_menu_button.clicked.connect(self.goToMainMenu)
        buttons_layout.addWidget(self.main_menu_button)

        self.submit_button = QPushButton('Submit', self)
        self.submit_button.clicked.connect(self.submitPreferences)
        buttons_layout.addWidget(self.submit_button)

        layout.addLayout(buttons_layout)


        self.setLayout(layout)
        self.loadPreferences()

    def resetDeviceName(self):
        self.device_name_input.setText(platform.node())

    def pickDirectory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            self.save_to_path_input.setText(directory)

    def resetSavePath(self):
        self.save_to_path_input.setText(get_default_path())

    
    def changes_made(self):
        """Check if any changes were made compared to the loaded preferences."""
        current_preferences = {
            "device_name": self.device_name_input.text(),
            "save_to_directory": self.save_to_path_input.text(),
            "encryption": self.encryption_toggle.isChecked(),
        }
        return current_preferences != self.original_preferences

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
                self.submitPreferences()  # Save preferences 
                self.go_to_main_menu()    # Go to main menu

            elif reply == QMessageBox.StandardButton.No:
                self.go_to_main_menu()    # Go to main menu
        else:       
            self.go_to_main_menu()  # No changes, go directly to main menu


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
        window_width, window_height = 400, 300
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2
        self.setGeometry(x, y, window_width, window_height)


    def loadPreferences(self):
        config = get_config()
        self.device_name_input.setText(config["device_name"])
        self.save_to_path_input.setText(config["save_to_directory"])
        self.encryption_toggle.setChecked(config["encryption"])

        # Store original values to track changes
        self.original_preferences = config.copy()
