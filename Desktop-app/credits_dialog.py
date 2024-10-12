import sys
import webbrowser
from PyQt6.QtWidgets import (QDialog, QLabel, QVBoxLayout, QPushButton, QApplication, 
                             QHBoxLayout, QWidget, QGridLayout, QScrollArea)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon
from PyQt6.QtGui import QFont, QColor, QPalette, QLinearGradient, QBrush, QPainter, QPen

class CircularPlaceholder(QWidget):
    def __init__(self, size=100, parent=None):
        super().__init__(parent)
        self.size = size
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#ECF0F1"), 2))
        painter.setBrush(QBrush(QColor("#34495E")))
        painter.drawEllipse(2, 2, self.size-4, self.size-4)

class CreditsDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Project Credits")
        self.resize(1280, 720)  # Initial size (16:9 aspect ratio)
        self.setup_window_flags()  # Set window flags
        self.setup_ui()

    def setup_window_flags(self):
        # Set window flags to allow minimize and maximize (restore down)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMinimizeButtonHint | Qt.WindowType.WindowMaximizeButtonHint)

    def resizeEvent(self, event):
        # Preserve the 16:9 aspect ratio on resize
        width = self.width()
        height = int(width * 9 / 16)
        self.resize(width, height)
        super().resizeEvent(event)

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(40, 20, 40, 20)

        # Apply gradient background
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor("#4B0082"))
        gradient.setColorAt(1, QColor("#4B0082"))
        palette = self.palette()
        palette.setBrush(QPalette.ColorRole.Window, QBrush(gradient))
        self.setPalette(palette)

        self.setStyleSheet("""
            QDialog {
                color: #2C3E50;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            QLabel {
                color: #2C3E50;
                font-size: 24px;
                font-weight: bold;
            }
            QPushButton {
                background-color: #3498DB;
                color: #ECF0F1;
                border: none;
                padding: 5px 10px;
                font-size: 12px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #2980B9;
            }
        """)

        title = QLabel("OUR PERFECT TEAM")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 32px; font-weight: bold; color: #fffae6;")
        main_layout.addWidget(title)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("background-color: transparent; border: none;")
        main_layout.addWidget(scroll_area)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        programmers_section = self.create_section("Programmers", self.get_coder_data())
        scroll_layout.addWidget(programmers_section)

        docs_section = self.create_section("Project Documentation", self.get_docs_data())
        scroll_layout.addWidget(docs_section)

        scroll_area.setWidget(scroll_content)

    def create_section(self, title, data):
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 20)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #FAEDCE;")
        layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)

        team_layout = QHBoxLayout()
        team_layout.setSpacing(40)
        
        for name, role, github, linkedin in data:
            member_widget = self.create_member_widget(name, role, github, linkedin)
            team_layout.addWidget(member_widget)

        layout.addLayout(team_layout)
        return section

    def create_member_widget(self, name, role, github, linkedin):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        placeholder = CircularPlaceholder(100)
        layout.addWidget(placeholder, alignment=Qt.AlignmentFlag.AlignCenter)

        name_label = QLabel(name)
        name_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFF1DB;")
        layout.addWidget(name_label, alignment=Qt.AlignmentFlag.AlignCenter)

        role_label = QLabel(role)
        role_label.setStyleSheet("font-size: 14px; color: #7F8C8D;")
        layout.addWidget(role_label, alignment=Qt.AlignmentFlag.AlignCenter)
    
        buttons_layout = QHBoxLayout()
        github_btn = QPushButton("git")
        github_btn.clicked.connect(lambda: webbrowser.open(github))
        linkedin_btn = QPushButton("in")
        linkedin_btn.clicked.connect(lambda: webbrowser.open(linkedin))
        
        for btn in [github_btn, linkedin_btn]:
            btn.setFixedSize(40, 40)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #34495E;
                    border-radius: 15px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #2C3E50;
                }
            """)
        
        buttons_layout.addWidget(github_btn)
        buttons_layout.addWidget(linkedin_btn)
        layout.addLayout(buttons_layout)

        return widget

    def get_coder_data(self):
        return [
            ("Armaan", "Programmer", "https://github.com/Armaan4477", "https://www.linkedin.com/in/armaan-nakhuda-756492235/"),
            ("Nishal", "Programmer", "https://github.com/Ailover123", "https://www.linkedin.com/in/nishal-poojary-159530290"),
            ("Samay", "Programmer", "https://github.com/ChampionSamay1644", "https://www.linkedin.com/in/samaypandey1644"),
            ("Urmi", "Programmer", "https://github.com/ura-dev04", "https://www.linkedin.com/in/urmi-joshi-6697a7320"),
            ("Yash", "Programmer", "https://github.com/FrosT2k5", "https://www.linkedin.com/in/yash-patil-385171257"),
        ]

    def get_docs_data(self):
        return [
            ("Vedashree", "Documentation", "https://github.com/vedashree2004", "https://www.linkedin.com/in/vedashree-gaikwad-716783298?utm_source=share&utm_campaign=share_via&utm_content=profile&utm_medium=android_app")
        ]

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = CreditsDialog()
    dialog.exec()
