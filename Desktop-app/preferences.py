from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QCheckBox, QHBoxLayout, QMessageBox, QApplication, QComboBox, QSizePolicy
)
from PyQt6.QtGui import QScreen, QFont, QColor, QKeyEvent, QKeySequence, QDesktopServices
from PyQt6.QtCore import Qt, QUrl
import sys
import platform
from constant import get_config, write_config, get_default_path
from PyQt6.QtWidgets import QGraphicsDropShadowEffect
from credits_dialog import CreditsDialog
from constant import logger
import requests
import os
import time
from PyQt6.QtWidgets import QProgressDialog
from subprocess import run

class PreferencesApp(QWidget):
    def __init__(self):
        super().__init__()
        self.original_preferences = {}
        self.initUI()
        self.setFixedSize(525, 600)  # Make the window smaller

    def initUI(self):
        self.setWindowTitle('Settings')
        self.center_window()
        self.set_background()
        self.displayversion()

        # Adjust main layout margins and spacing
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Top layout as a vertical layout
        top_layout = QVBoxLayout()
        top_layout.setSpacing(10)

        # Version label and Check for Update button side by side
        version_update_layout = QHBoxLayout()
        version_update_layout.setSpacing(5)

        self.version_label = QLabel('Version: ' + self.uga_version)
        self.version_label.setFont(QFont("Arial", 14))
        self.style_label(self.version_label)
        self.version_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)  # Allow label to expand
        version_update_layout.addWidget(self.version_label)

        self.update_button = QPushButton('Check for Update', self)
        self.update_button.setFont(QFont("Arial", 10))
        self.update_button.setFixedSize(130, 30)  # Adjust button width if needed
        self.style_update_button(self.update_button)
        self.update_button.clicked.connect(self.fetch_platform_value)
        version_update_layout.addWidget(self.update_button)

        top_layout.addLayout(version_update_layout)

        # Update Channel label and dropdown side by side
        channel_layout = QHBoxLayout()
        channel_layout.setSpacing(5)

        self.channel_label = QLabel('Update Channel:')
        self.channel_label.setFont(QFont("Arial", 14))
        self.style_label(self.channel_label)
        self.channel_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)  # Allow label to expand
        channel_layout.addWidget(self.channel_label)

        self.channel_dropdown = QComboBox()
        self.channel_dropdown.addItems(['Stable', 'Beta'])
        self.style_dropdown(self.channel_dropdown)
        self.channel_dropdown.currentIndexChanged.connect(self.update_channel_preference)
        channel_layout.addWidget(self.channel_dropdown)

        top_layout.addLayout(channel_layout)

        layout.addLayout(top_layout)

        # Device Name
        self.device_name_label = QLabel('Device Name:', self)
        self.device_name_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        self.style_label(self.device_name_label)
        layout.addWidget(self.device_name_label)

        # Horizontal layout for device name input and reset button
        device_name_layout = QHBoxLayout()
        device_name_layout.setSpacing(10)

        self.device_name_input = QLineEdit(self)
        self.device_name_input.setFont(QFont("Arial", 16))
        self.device_name_input.setFixedHeight(30)
        self.device_name_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
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
        self.save_to_path_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.style_input(self.save_to_path_input)
        layout.addWidget(self.save_to_path_input)

        path_layout = QHBoxLayout()
        path_layout.setSpacing(10)
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

        # Show Warning Toggle
        self.show_update_toggle = QCheckBox('Auto-check for updates during app launch', self)
        self.show_update_toggle.setFont(QFont("Arial", 18))
        self.style_checkbox(self.show_update_toggle)
        layout.addWidget(self.show_update_toggle)

        # Adjust the Credits button below the auto-update toggle
        self.credit_button = QPushButton('Credits', self)
        self.credit_button.setFont(QFont("Arial", 12))
        self.credit_button.setFixedSize(65, 35)  # Revert to smaller size
        self.style_credit_button(self.credit_button)  # Use specific styling method
        self.credit_button.clicked.connect(self.show_credits)
        layout.addWidget(self.credit_button)

        # Submit and Main Menu buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        self.main_menu_button = QPushButton('Main Menu', self)
        self.main_menu_button.setFont(QFont("Arial", 12))
        self.main_menu_button.setFixedSize(150, 50)
        self.main_menu_button.clicked.connect(self.goToMainMenu)
        self.style_button(self.main_menu_button)
        buttons_layout.addWidget(self.main_menu_button)

        # Credits Button
        self.help_button = QPushButton('Help')
        self.help_button.setFont(QFont("Arial", 12))
        self.style_button(self.help_button)
        self.help_button.clicked.connect(self.show_help_dialog)
        buttons_layout.addWidget(self.help_button)

        layout.addLayout(buttons_layout)

        self.setLayout(layout)
        self.loadPreferences()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.goToMainMenu()

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
            }
            QLineEdit:focus {
                border: 2px solid #333333;  /* Dark grey border on focus */
                background-color: rgba(255, 255, 255, 0.1); /* Slightly opaque background on focus */
            }
        """)

    def style_checkbox(self, checkbox):
        tick = os.path.join(os.path.dirname(__file__), "icons", "tick.svg")
        tick = tick.replace('\\', '/')  # Convert backslashes to forward slashes for CSS
        checkbox.setGraphicsEffect(self.create_glow_effect())
        checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: #FFFFFF;
                background-color: transparent;
                spacing: 5px;
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border: 2px solid #FFFFFF;
                border-radius: 4px;
                background-color: transparent;
            }}
            QCheckBox::indicator:unchecked {{
                background-color: transparent;
            }}
            QCheckBox::indicator:checked {{
                background-color: transparent;
                border: 2px solid #FFFFFF;
                image: url({tick});
            }}
            QCheckBox::indicator:unchecked:hover {{
                background-color: rgba(255, 255, 255, 0.1);
            }}
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

    def style_credit_button(self, button):
        button.setFixedSize(65, 35)
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

    def style_update_button(self, button):
        button.setFixedSize(150, 30)
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

    def style_dropdown(self, dropdown):
        dropdown.setFont(QFont("Arial", 12))
        dropdown.setFixedWidth(120)
        dropdown.setFixedHeight(30)
        dropdown.setStyleSheet("""
            QComboBox {
                color: white;
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(47, 54, 66, 255),
                    stop: 1 rgba(75, 85, 98, 255)
                );
                border-radius: 4px;
                padding: 5px;
                min-width: 6em;
            }
            QComboBox:hover {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(60, 68, 80, 255),
                    stop: 1 rgba(90, 100, 118, 255)
                );
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 10px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid white;
                width: 0;
                height: 0;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                color: white;
                background-color: rgb(47, 54, 66);
                selection-background-color: rgb(75, 85, 98);
                outline: none;
            }
        """)
        dropdown.setGraphicsEffect(self.create_glow_effect())

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
        if (directory):
            self.save_to_path_input.setText(directory)

    def resetSavePath(self):
        self.save_to_path_input.setText(get_default_path())

    def displayversion(self):
        config = get_config()
        self.uga_version = config["app_version"]

    def loadPreferences(self):
        config = get_config()
        self.version = config["version"]
        self.app_version = config["app_version"]
        self.device_name_input.setText(config["device_name"])
        self.save_to_path_input.setText(config["save_to_directory"])
        self.max_filesize = config["max_filesize"]
        self.encryption_toggle.setChecked(config["encryption"])
        self.android_encryption = (config["android_encryption"])
        self.swift_encryption = (config["swift_encryption"])
        self.show_warning_toggle.setChecked(config["show_warning"])  # Load show_warning value
        self.show_update_toggle.setChecked(config["check_update"])
        self.update_channel = config["update_channel"]
        channel_index = 0 if config["update_channel"] == "stable" else 1
        self.channel_dropdown.setCurrentIndex(channel_index)
        self.original_preferences = config.copy()
        logger.info("Loaded preferences- json_version: %s", self.version)
        logger.info("Loaded preferences- app_version: %s", self.app_version)
        logger.info("Loaded preferences- android_encryption: %s", self.android_encryption)
        logger.info("Loaded preferences- swift_encryption: %s", self.swift_encryption)
        logger.info("Loaded preferences- show_warning: %s", self.show_warning_toggle.isChecked())
        logger.info("Loaded preferences- check_update: %s", self.show_update_toggle.isChecked())

    def submitPreferences(self):
        device_name = self.device_name_input.text()
        save_to_path = self.save_to_path_input.text()
        encryption = self.encryption_toggle.isChecked()
        show_warning = self.show_warning_toggle.isChecked()  # Get show_warning toggle state
        check_update = self.show_update_toggle.isChecked()

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

        # Create a dictionary of only the changed values
        changed_preferences = {}
        current_config = get_config()  # Get current config

        # Compare each field with original preferences and only include changed ones
        if device_name != self.original_preferences["device_name"]:
            changed_preferences["device_name"] = device_name
        
        if save_to_path != self.original_preferences["save_to_directory"]:
            changed_preferences["save_to_directory"] = save_to_path
        
        if encryption != self.original_preferences["encryption"]:
            changed_preferences["encryption"] = encryption
        
        if show_warning != self.original_preferences["show_warning"]:
            changed_preferences["show_warning"] = show_warning
        
        if check_update != self.original_preferences["check_update"]:
            changed_preferences["check_update"] = check_update

        # If there are any changes, update the config
        if changed_preferences:
            # Update only changed fields in current config
            current_config.update(changed_preferences)
            write_config(current_config)
            # Update original preferences with new values
            self.original_preferences.update(changed_preferences)

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
        else:
            # If no changes were made, just go back to main menu
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
        self.main_app = MainApp(skip_version_check=True)
        self.main_app.show()

    def center_window(self):
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        window_width, window_height = 525, 600  # Updated to 16:9 ratio
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2
        self.setGeometry(x, y, window_width, window_height)

    def changes_made(self):
        current_preferences = {
            "version": self.version,
            "app_version": self.app_version,
            "device_name": self.device_name_input.text(),
            "save_to_directory": self.save_to_path_input.text(),
            "max_filesize": self.max_filesize,
            "encryption": self.encryption_toggle.isChecked(),
            "android_encryption": self.android_encryption,
            "swift_encryption": self.swift_encryption,
            "show_warning": self.show_warning_toggle.isChecked(),
            "check_update": self.show_update_toggle.isChecked()
        }
        
        # Create comparison dict without update_channel
        original_without_channel = self.original_preferences.copy()
        original_without_channel.pop("update_channel", None)
        
        return current_preferences != original_without_channel
    
    def show_credits(self):
        logger.info("Opened Credits Dialog")
        credits_dialog = CreditsDialog()
        credits_dialog.exec()

    def show_help_dialog(self):
        help_dialog = QMessageBox(self)
        help_dialog.setWindowTitle("Help")
        help_dialog.setText("""
        <b>Version:</b> The current version number of the application.
        <br><br>
        <b>Check for Update:</b> Check for the latest version of the application.
        <br><br>
        <b>Update Channel:</b> Choose between the stable and beta update channels.
        <br><br>
        <b>Device Name:</b> The name assigned to this device. You can reset it to the system's default.
        <br><br>
        <b>Save to Path:</b> Choose a directory to save your files. You can also reset it to the default path.
        <br><br>
        <b>Encryption:</b> Enable or disable AES256 encryption for files being sent.
        <br><br>
        <b>Show Warnings:</b> Enable or disable warning messages before sending or receiving files.
        <br><br>
        <b>Auto-check for updates during app launch:</b> Enable or disable automatic version checks when the application is launched.
        <br><br>
        <b>Credits:</b> View credits for the application.
        <br><br>
        <b>Main Menu:</b> Go back to the main application window. You will be prompted to save changes if any.
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

    def fetch_platform_value(self):
        url = self.get_platform_link()
        logger.info(f"Fetching platform value from: {url}")
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            if "value" in data:
                logger.info(f"Value for python: {data['value']}")
                fetched_version = data['value']
                
                if self.compare_versions(fetched_version, self.uga_version) == 0:
                    message = "You are on the latest version."
                    buttons = QMessageBox.StandardButton.Ok
                elif self.compare_versions(fetched_version, self.uga_version) > 0:
                    message = "You are on an older version. Please update."
                    buttons = QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Open | QMessageBox.StandardButton.Apply
                elif self.compare_versions(fetched_version, self.uga_version) < 0:
                    message = "You are on a newer version. Please downgrade to the latest available version."
                    buttons = QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Open | QMessageBox.StandardButton.Apply
                else:
                    message = "Server error, Please try again later."
                    buttons = QMessageBox.StandardButton.Ok

                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Version Check")
                msg_box.setText(message)
                msg_box.setIcon(QMessageBox.Icon.Information)
                msg_box.setStandardButtons(buttons)

                open_button = msg_box.button(QMessageBox.StandardButton.Open)
                if open_button:
                    open_button.setText("Open Downloads Page")

                download_button = msg_box.button(QMessageBox.StandardButton.Apply)
                if download_button:
                    download_button.setText("Download Latest Version")

                # Apply the same styling as before
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
                
                reply = msg_box.exec()

                if reply == QMessageBox.StandardButton.Open:
                    self.download_page()
                elif reply == QMessageBox.StandardButton.Apply:
                    logger.info(f"Download path: {self.get_update_download()}")
                return fetched_version

            else:
                logger.error(f"Value key not found in response: {data}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching platform value: {e}")
            message = "Server error, Please check your internet connection or try again later."
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Version Check")
            msg_box.setText(message)
            msg_box.setIcon(QMessageBox.Icon.Critical)
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

    def compare_versions(self, v1, v2):
        v1_parts = [int(part) for part in v1.split('.')]
        v2_parts = [int(part) for part in v2.split('.')]
        
        # Pad the shorter version with zeros
        while len(v1_parts) < 4:
            v1_parts.append(0)
        while len(v2_parts) < 4:
            v2_parts.append(0)
        
        return (v1_parts > v2_parts) - (v1_parts < v2_parts)
    
    def get_platform_link(self):
        channel = get_config()["update_channel"]
        logger.info(f"Checking for updates in channel: {channel}")
        if platform.system() == 'Windows':
                platform_name = 'windows'
        elif platform.system() == 'Linux':
                platform_name = 'linux'
        elif platform.system() == 'Darwin':
                platform_name = 'macos'
        else:
                logger.error("Unsupported OS!")
                return None

        # for testing use the following line and comment the above lines, auga=older version, buga=newer version and cuga=latest version
        # platform_name = 'auga'
        # platform_name = 'buga'
        # platform_name = 'cuga'

        if channel == "stable":
            url = f"https://datadashshare.vercel.app/api/platformNumber?platform=python_{platform_name}"
            
        elif channel == "beta":
            url = f"https://datadashshare.vercel.app/api/platformNumberbeta?platform=python_{platform_name}"
        return url
    
    def get_update_download(self):
        channel = get_config()["update_channel"]
        logger.info(f"Checking for updates in channel: {channel}")
        # Determine platform OS and download path
        if platform.system() == 'Windows':
            platform_os = 'windows'
            download_path = os.path.join(os.getenv('USERPROFILE'), 'Downloads')
            file_extension = '.exe'
        elif platform.system() == 'Linux':
            platform_os = 'linux'
            download_path = os.path.join(os.path.expanduser('~'), 'Downloads')
            file_extension = ''
        elif platform.system() == 'Darwin':
            platform_os = 'macos'
            download_path = os.path.join(os.path.expanduser('~'), 'Downloads')
            file_extension = '.dmg'
        else:
            logger.error("Unsupported OS!")
            return None

        # Determine platform type
        machine = platform.machine().lower()
        if machine in ['arm64', 'aarch64']:
            platform_type = 'arm'
        elif machine in ['x86_64', 'amd64']:
            platform_type = 'x64'
        else:
            logger.error("Unsupported platform type!")
            return None

        # Map platform combinations to download links

        if channel == "stable":
        #main version
            download_links = {
                ('windows', 'x64'): 'https://github.com/Project-Bois/DataDash-files/raw/refs/heads/main/DataDash(windows%20x64).exe',
                ('windows', 'arm'): 'https://github.com/Project-Bois/DataDash-files/raw/refs/heads/main/DataDash(windows%20arm).exe',
                ('linux', 'x64'): 'https://github.com/Project-Bois/DataDash-files/raw/refs/heads/main/DataDash(linux%20x64)',
                ('linux', 'arm'): 'https://github.com/Project-Bois/DataDash-files/raw/refs/heads/main/DataDash(linux%20arm)',
                ('macos', 'x64'): 'https://github.com/Project-Bois/DataDash-files/raw/refs/heads/main/DataDash(macos%20x64).dmg',
                ('macos', 'arm'): 'https://github.com/Project-Bois/DataDash-files/raw/refs/heads/main/DataDash(macos%20arm).dmg',
            }

        elif channel == "beta":
        #beta version
            download_links = {
                ('windows', 'x64'): 'https://github.com/Project-Bois/data-dash-test-files/raw/refs/heads/main/Windows.exe',
                ('windows', 'arm'): 'https://github.com/Project-Bois/data-dash-test-files/raw/refs/heads/main/Windows.exe',
                ('linux', 'x64'): 'https://github.com/Project-Bois/data-dash-test-files/raw/refs/heads/main/Linux',
                ('macos', 'arm'): 'https://github.com/Project-Bois/data-dash-test-files/raw/refs/heads/main/Macos(arm).dmg',
            }

        key = (platform_os, platform_type)
        download_link = download_links.get(key)

        if not download_link:
            logger.error("Unsupported OS or architecture!")
            return None

        # Download the file into the download folder
        try:
            response = requests.get(download_link, stream=True)
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            block_size = 8192  # 8 KB
            progress_dialog = QProgressDialog("Downloading update...", "Cancel", 0, total_size, self)
            progress_dialog.setWindowTitle("Download Progress")
            progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            progress_dialog.setStyleSheet("""
                QProgressDialog {
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
                    color: #FFFFFF;
                    font-size: 16px;
                }
                QProgressBar {
                    border: 1px solid #444;
                    border-radius: 5px;
                    text-align: center;
                    background-color: #222;
                    color: #FFFFFF;
                    font-size: 14px;
                }
                QProgressBar::chunk {
                    background-color: #3add36;
                    width: 20px;
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
            progress_dialog.show()
            downloaded_size = 0
            start_time = time.time()
            filename = os.path.join(download_path, 'DataDash' + file_extension)
            with open(filename, 'wb') as f:
                for data in response.iter_content(block_size):
                    if progress_dialog.wasCanceled():
                        msg_box = QMessageBox(self)
                        msg_box.setWindowTitle("Download Canceled")
                        msg_box.setText("Download canceled by user.")
                        msg_box.setIcon(QMessageBox.Icon.Information)
                        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
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
                        logger.info("Download canceled by user")
                        f.close()
                        os.remove(filename)
                        return None
                    f.write(data)
                    downloaded_size += len(data)
                    elapsed_time = time.time() - start_time
                    if elapsed_time > 0:
                        # Calculate speed in KB/s
                        speed_kbps = (downloaded_size / 1024) / elapsed_time
                        # Convert speed to MB/s with up to 3 decimal places
                        speed_mbps = round(speed_kbps / 1024, 1)
                        # Calculate estimated time remaining in seconds
                        estimated_total_time = (total_size / downloaded_size) * elapsed_time
                        time_remaining = estimated_total_time - elapsed_time
                        # Format time remaining into minutes and seconds
                        mins, secs = divmod(time_remaining, 60)
                        time_format = f"{int(mins)} min {int(secs)} sec" if mins >= 1 else f"{int(secs)} sec"
                        # Update label with speed and estimated time remaining
                        progress_dialog.setLabelText(f"Downloading update... {speed_mbps} MB/s - {time_format} remaining")
                    progress_dialog.setValue(downloaded_size)
                    QApplication.processEvents()
            progress_dialog.close()

            # Set chmod permission for linux
            if platform_os == "linux":
                run(['chmod', '+x', filename])

            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Download Complete")
            msg_box.setText(f"File downloaded to {filename}")
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
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
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Download Failed")
            msg_box.setText("Failed to download the update.")
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
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
            return None

        return filename
        
    def update_channel_preference(self, index):
        channel = "stable" if index == 0 else "beta"
        config = get_config()
        if config["update_channel"] != channel:
            config["update_channel"] = channel
            write_config(config)
            self.original_preferences["update_channel"] = channel
            logger.info(f"Update channel changed to: {channel}")

    def download_page(self):
        channel = get_config()["update_channel"]
        if channel == "beta":
            QDesktopServices.openUrl(QUrl("https://datadashshare.vercel.app/beta"))
            logger.info("Opened beta page")
        elif channel == "stable":
            QDesktopServices.openUrl(QUrl("https://datadashshare.vercel.app/download"))
            logger.info("Opened stable page")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PreferencesApp()
    window.show()
    sys.exit(app.exec())
