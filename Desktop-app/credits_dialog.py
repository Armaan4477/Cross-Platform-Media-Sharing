import sys
import webbrowser
from PyQt6.QtWidgets import (QDialog, QLabel, QVBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QApplication, 
                             QHeaderView, QHBoxLayout, QWidget)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QColor, QPalette, QLinearGradient, QBrush

class CreditsDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Project Credits")
        self.setFixedSize(500, 600)
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Apply gradient background
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor("#2C3E50"))
        gradient.setColorAt(1, QColor("#34495E"))
        palette = self.palette()
        palette.setBrush(QPalette.ColorRole.Window, QBrush(gradient))
        self.setPalette(palette)

        self.setStyleSheet("""
            QDialog {
                color: #ECF0F1;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            QLabel {
                color: #ECF0F1;
                font-size: 24px;
                font-weight: bold;
            }
            QTableWidget {
                background-color: rgba(52, 73, 94, 0.7);
                color: #ECF0F1;
                border: none;
                gridline-color: rgba(236, 240, 241, 0.1);
            }
            QTableWidget::item {
                padding: 10px;
            }
            QHeaderView::section {
                background-color: rgba(44, 62, 80, 0.8);
                color: #ECF0F1;
                padding: 10px;
                border: none;
                font-weight: bold;
            }
            QPushButton {
                background-color: #3498DB;
                color: #ECF0F1;
                border: none;
                padding: 10px 20px;
                font-size: 16px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2980B9;
            }
        """)

        title = QLabel("Project Credits")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        coder_table = self.create_table("Coder/Debugger", self.get_coder_data(), 280)
        main_layout.addWidget(coder_table)

        docs_table = self.create_table("Project Documentation", self.get_docs_data(), 100)
        main_layout.addWidget(docs_table)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        close_button.setFixedSize(QSize(120, 40))
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

    def create_table(self, title, data, height):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        table = QTableWidget()
        table.setRowCount(len(data))
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Name", "GitHub", "LinkedIn"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.setFixedHeight(height)

        for row, (name, github, linkedin) in enumerate(data):
            table.setItem(row, 0, QTableWidgetItem(name))
            github_item = QTableWidgetItem("View")
            linkedin_item = QTableWidgetItem("View")
            github_item.setForeground(QColor("#3498DB"))
            linkedin_item.setForeground(QColor("#3498DB"))
            table.setItem(row, 1, github_item)
            table.setItem(row, 2, linkedin_item)

        table.cellClicked.connect(lambda row, col: self.open_link(data[row][col]))
        layout.addWidget(table)

        return container

    def get_coder_data(self):
        return [
            ("Armaan", "https://github.com/Armaan4477", "https://www.linkedin.com/in/armaan-nakhuda-756492235/"),
            ("Nishal", "https://github.com/Ailover123", "https://www.linkedin.com/in/nishal-poojary-159530290"),
            ("Samay", "https://github.com/ChampionSamay1644", "https://www.linkedin.com/in/samaypandey1644"),
            ("Urmi", "https://github.com/ura-dev04", "https://www.linkedin.com/in/urmi-joshi-6697a7320"),
            ("Yash", "https://github.com/FrosT2k5", "https://www.linkedin.com/in/yash-patil-385171257"),
        ]

    def get_docs_data(self):
        return [
            ("Vedashree", "https://github.com/vedashree2004", "https://www.linkedin.com/in/vedashree-gaikwad-716783298?utm_source=share&utm_campaign=share_via&utm_content=profile&utm_medium=android_app")
        ]

    def open_link(self, url):
        webbrowser.open(url)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = CreditsDialog()
    dialog.exec()


