from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog,
    QCheckBox, QHBoxLayout, QMessageBox, QApplication, QFrame
)
from PyQt6.QtGui import QFont, QColor, QScreen
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGraphicsDropShadowEffect
import sys
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
        self.set_background()

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QFrame()
        header.setFixedHeight(60)
        header.setStyleSheet("background-color: #333;")
        header_layout = QHBoxLayout(header)
        title_label = QLabel("Preferences")
        title_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title_label.setStyleSheet("color: white;")
        header_layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(header)

        # Device Name
        main_layout.addSpacing(20)
        self.device_name_label = QLabel('Device Name:', self)
        self.device_name_label.setFont(QFont("Arial", 12))
        main_layout.addWidget(self.device_name_label)
        self.device_name_input = QLineEdit(self)
        main_layout.addWidget(self.device_name_input)

        self.device_name_reset_button = QPushButton('Reset', self)
        self.style_button(self.device_name_reset_button)
        self.device_name_reset_button.clicked.connect(self.resetDeviceName)
        main_layout.addWidget(self.device_name_reset_button)

        # Save to Path
        main_layout.addSpacing(10)
        self.save_to_path_label = QLabel('Save to Path:', self)
        self.save_to_path_label.setFont(QFont("Arial", 12))
        main_layout.addWidget(self.save_to_path_label)

        self.save_to_path_input = QLineEdit(self)
        main_layout.addWidget(self.save_to_path_input)

        path_layout = QHBoxLayout()
        self.save_to_path_picker_button = QPushButton('Pick Directory', self)
        self.style_button(self.save_to_path_picker_button)
        self.save_to_path_picker_button.clicked.connect(self.pickDirectory)
        path_layout.addWidget(self.save_to_path_picker_button)

        self.save_to_path_reset_button = QPushButton('Reset', self)
        self.style_button(self.save_to_path_reset_button)
        self.save_to_path_reset_button.clicked.connect(self.resetSavePath)
        path_layout.addWidget(self.save_to_path_reset_button)
        main_layout.addLayout(path_layout)

        # Encryption Toggle
        main_layout.addSpacing(10)
        self.encryption_toggle = QCheckBox('Enable Encryption', self)
        self.encryption_toggle.setFont(QFont("Arial", 12))
        main_layout.addWidget(self.encryption_toggle)

        # Buttons
        main_layout.addSpacing(20)
        buttons_layout = QHBoxLayout()
        self.main_menu_button = QPushButton('Main Menu', self)
        self.style_button(self.main_menu_button)
        self.main_menu_button.clicked.connect(self.goToMainMenu)
        buttons_layout.addWidget(self.main_menu_button)

        self.submit_button = QPushButton('Save')
        self.style_button(self.submit_button)
        self.submit_button.clicked.connect(self.submitPreferences)
        buttons_layout.addWidget(self.submit_button)
        main_layout.addLayout(buttons_layout)

        self.setLayout(main_layout)
        self.loadPreferences()

    def style_button(self, button):
        button.setFixedSize(130, 40)
        button.setFont(QFont("Arial", 11))
        button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(47, 54, 66, 255), 
                    stop: 1 rgba(75, 85, 98, 255)
                );
                color: white;
                border-radius: 10px;
                border: 2px solid rgba(0, 0, 0, 0.5);
                padding: 5px;
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
        glow_effect.setBlurRadius(10)
        glow_effect.setXOffset(0)
        glow_effect.setYOffset(0)
        glow_effect.setColor(QColor(255, 255, 255, 80))
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
        window_width, window_height = 400, 300
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
    preferences = PreferencesApp()
    preferences.show()
    sys.exit(app.exec())
